from __future__ import annotations

import html
import json
import mimetypes
import os
import re
import sqlite3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "drugbank_full.db"
STATIC_DIR = ROOT / "static"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def clean_text(text: str | None) -> str:
    if not text:
        return ""

    cleaned = html.unescape(str(text))
    cleaned = re.sub(r"<\s*br\s*/?\s*>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*(sub|sup)\s*>(.*?)<\s*/\s*\1\s*>", r"\2", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"</?\s*(sub|sup)\s*>?", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"_(.*?)_", r"\1", cleaned)
    cleaned = re.sub(r"\s+\*\s+", " ", cleaned)

    def clean_reference(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        citation = r"(?:label|fda label|[A-Z]\d+|DB\d+)"
        if re.fullmatch(fr"{citation}(?:\s*,\s*{citation})*", inner, flags=re.IGNORECASE):
            return ""
        return inner

    cleaned = re.sub(r"\[([^\[\]]+)\]", clean_reference, cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def compact(text: str | None, limit: int = 500) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "..."


def severity_for(description: str | None) -> tuple[str, str]:
    text = (description or "").lower()
    high_terms = ("contraindicated", "life-threatening", "fatal", "hemorrhage", "bleeding", "toxicity")
    moderate_terms = ("risk", "severity", "increase", "decrease", "adverse", "serum concentration")

    if any(term in text for term in high_terms):
        return "high", "High attention"
    if any(term in text for term in moderate_terms):
        return "moderate", "Monitor"
    return "informational", "Informational"


def row_to_drug(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["drugbank_id"],
        "name": row["name"] or row["drugbank_id"],
        "description": compact(row["description"], 2200),
        "indication": compact(row["indication"], 2600),
        "mechanism": compact(row["mechanism_of_action"], 2600),
        "toxicity": compact(row["toxicity"], 1800),
        "metabolism": compact(row["metabolism"], 1800),
        "half_life": compact(row["half_life"], 900),
    }


class NeuroPharmHandler(BaseHTTPRequestHandler):
    server_version = "NeuroPharmDB/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        try:
            if path == "/":
                self.send_index()
            elif path.startswith("/static/"):
                self.send_static(path.removeprefix("/static/"))
            elif path == "/api/stats":
                self.send_json(self.stats())
            elif path == "/api/search":
                params = parse_qs(parsed.query)
                self.send_json(self.search(params.get("q", [""])[0]))
            elif path == "/api/options":
                params = parse_qs(parsed.query)
                self.send_json(self.options(params.get("q", [""])[0]))
            elif path == "/api/check":
                params = parse_qs(parsed.query)
                self.send_json(
                    self.check_pair(
                        params.get("drug1", [""])[0],
                        params.get("drug2", [""])[0],
                    )
                )
            elif path == "/api/check-many":
                params = parse_qs(parsed.query)
                self.send_json(self.check_many(params.get("ids", [""])[0]))
            elif path.startswith("/api/drugs/") and path.endswith("/interactions"):
                drug_id = path.removeprefix("/api/drugs/").removesuffix("/interactions").strip("/")
                params = parse_qs(parsed.query)
                self.send_json(self.drug_interactions(drug_id, params.get("q", [""])[0]))
            elif path.startswith("/api/drugs/"):
                drug_id = path.removeprefix("/api/drugs/").strip("/")
                self.send_json(self.drug_detail(drug_id))
            else:
                self.send_error(404, "Not found")
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_index(self) -> None:
        html_doc = (STATIC_DIR / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_doc)))
        self.end_headers()
        self.wfile.write(html_doc)

    def send_static(self, filename: str) -> None:
        safe_path = (STATIC_DIR / filename).resolve()
        if not str(safe_path).startswith(str(STATIC_DIR.resolve())) or not safe_path.is_file():
            self.send_error(404, "Static file not found")
            return

        content = safe_path.read_bytes()
        mime_type = mimetypes.guess_type(safe_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def stats(self) -> dict:
        with get_db() as db:
            drugs = db.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
            interactions = db.execute("SELECT COUNT(*) FROM drug_interactions").fetchone()[0]
            food = db.execute("SELECT COUNT(*) FROM food_interactions").fetchone()[0]
        return {"drugs": drugs, "interactions": interactions, "foodInteractions": food}

    def search(self, query: str) -> dict:
        q = " ".join(query.strip().split())
        if len(q) < 2:
            return {"results": []}

        prefix = f"{q}%"
        contains = f"%{q}%"
        with get_db() as db:
            rows = db.execute(
                """
                WITH matched AS (
                    SELECT drugbank_id, name, NULL AS matched_synonym, 0 AS rank
                    FROM drugs
                    WHERE name LIKE ?
                    UNION
                    SELECT drugbank_id, name, NULL AS matched_synonym, 1 AS rank
                    FROM drugs
                    WHERE name LIKE ?
                    UNION
                    SELECT d.drugbank_id, d.name, s.synonym AS matched_synonym, 2 AS rank
                    FROM synonyms s
                    JOIN drugs d ON d.drugbank_id = s.drug_id
                    WHERE s.synonym LIKE ?
                )
                SELECT drugbank_id, name, matched_synonym, MIN(rank) AS rank
                FROM matched
                GROUP BY drugbank_id, name
                ORDER BY rank, LENGTH(name), name
                LIMIT 60
                """,
                (prefix, contains, contains),
            ).fetchall()

        return {
            "results": [
                {
                    "id": row["drugbank_id"],
                    "name": row["name"] or row["drugbank_id"],
                    "synonym": row["matched_synonym"],
                }
                for row in rows
            ]
        }

    def options(self, query: str) -> dict:
        q = " ".join(query.strip().split())
        if q:
            return self.search(q)

        preferred = [
            "Acetylsalicylic acid",
            "Warfarin",
            "Apixaban",
            "Metformin",
            "Atorvastatin",
            "Ibuprofen",
            "Acetaminophen",
            "Amoxicillin",
            "Omeprazole",
            "Clopidogrel",
            "Simvastatin",
            "Lisinopril",
            "Amlodipine",
            "Prednisone",
            "Fluoxetine",
            "Sertraline",
            "Ciprofloxacin",
            "Levothyroxine",
        ]

        with get_db() as db:
            preferred_rows = db.execute(
                """
                SELECT drugbank_id, name, NULL AS matched_synonym
                FROM drugs
                WHERE name IN ({})
                """.format(",".join("?" for _ in preferred)),
                preferred,
            ).fetchall()
            preferred_by_name = {row["name"]: row for row in preferred_rows}
            rows = [preferred_by_name[name] for name in preferred if name in preferred_by_name]

            alphabetic_rows = db.execute(
                """
                SELECT drugbank_id, name, NULL AS matched_synonym
                FROM drugs
                WHERE name IS NOT NULL
                  AND TRIM(name) != ''
                  AND name NOT IN ({})
                ORDER BY name COLLATE NOCASE
                LIMIT 102
                """.format(",".join("?" for _ in preferred)),
                preferred,
            ).fetchall()
            rows.extend(alphabetic_rows)

        return {
            "results": [
                {
                    "id": row["drugbank_id"],
                    "name": row["name"] or row["drugbank_id"],
                    "synonym": row["matched_synonym"],
                }
                for row in rows
            ]
        }

    def check_many(self, raw_ids: str) -> dict:
        ids: list[str] = []
        for drug_id in raw_ids.split(","):
            clean_id = drug_id.strip()
            if clean_id and clean_id not in ids:
                ids.append(clean_id)

        if len(ids) < 2:
            return {"error": "Select at least two drugs to check."}
        if len(ids) > 12:
            return {"error": "Please check 12 drugs or fewer at a time."}

        placeholders = ",".join("?" for _ in ids)
        with get_db() as db:
            drug_rows = db.execute(
                f"""
                SELECT * FROM drugs
                WHERE drugbank_id IN ({placeholders})
                """,
                ids,
            ).fetchall()
            drugs_by_id = {row["drugbank_id"]: row for row in drug_rows}

            missing = [drug_id for drug_id in ids if drug_id not in drugs_by_id]
            if missing:
                return {"error": f"Could not find: {', '.join(missing)}"}

            interaction_rows = db.execute(
                f"""
                SELECT drug1_id, drug2_id, description
                FROM drug_interactions
                WHERE drug1_id IN ({placeholders})
                  AND drug2_id IN ({placeholders})
                """,
                [*ids, *ids],
            ).fetchall()

        interactions: dict[frozenset[str], sqlite3.Row] = {}
        for row in interaction_rows:
            key = frozenset((row["drug1_id"], row["drug2_id"]))
            interactions.setdefault(key, row)

        pairs = []
        for index, drug1_id in enumerate(ids):
            for drug2_id in ids[index + 1 :]:
                row = interactions.get(frozenset((drug1_id, drug2_id)))
                drug1 = row_to_drug(drugs_by_id[drug1_id])
                drug2 = row_to_drug(drugs_by_id[drug2_id])
                item = {
                    "drug1": drug1,
                    "drug2": drug2,
                    "found": row is not None,
                }
                if row is not None:
                    level, label = severity_for(row["description"])
                    item["interaction"] = {
                        "description": clean_text(row["description"]),
                        "severity": level,
                        "label": label,
                    }
                pairs.append(item)

        return {
            "drugs": [row_to_drug(drugs_by_id[drug_id]) for drug_id in ids],
            "pairs": pairs,
            "summary": {
                "selected": len(ids),
                "checked": len(pairs),
                "found": sum(1 for pair in pairs if pair["found"]),
            },
        }

    def check_pair(self, drug1: str, drug2: str) -> dict:
        if not drug1 or not drug2:
            return {"error": "Select two drugs to check."}
        if drug1 == drug2:
            return {"error": "Choose two different drugs."}

        with get_db() as db:
            d1 = db.execute("SELECT * FROM drugs WHERE drugbank_id = ?", (drug1,)).fetchone()
            d2 = db.execute("SELECT * FROM drugs WHERE drugbank_id = ?", (drug2,)).fetchone()
            interaction = db.execute(
                """
                SELECT * FROM drug_interactions
                WHERE (drug1_id = ? AND drug2_id = ?)
                   OR (drug1_id = ? AND drug2_id = ?)
                LIMIT 1
                """,
                (drug1, drug2, drug2, drug1),
            ).fetchone()

        if d1 is None or d2 is None:
            return {"error": "One or both selected drugs were not found."}

        result = {
            "drug1": row_to_drug(d1),
            "drug2": row_to_drug(d2),
            "found": interaction is not None,
        }
        if interaction is not None:
            level, label = severity_for(interaction["description"])
            result["interaction"] = {
                "description": clean_text(interaction["description"]),
                "severity": level,
                "label": label,
            }
        return result

    def drug_detail(self, drug_id: str) -> dict:
        with get_db() as db:
            drug = db.execute("SELECT * FROM drugs WHERE drugbank_id = ?", (drug_id,)).fetchone()
            if drug is None:
                return {"error": "Drug not found."}

            categories = db.execute(
                "SELECT category FROM categories WHERE drug_id = ? ORDER BY category LIMIT 10",
                (drug_id,),
            ).fetchall()
            food = db.execute(
                "SELECT description FROM food_interactions WHERE drug_id = ? LIMIT 8",
                (drug_id,),
            ).fetchall()
            targets = db.execute(
                "SELECT name, organism, action FROM targets WHERE drug_id = ? LIMIT 8",
                (drug_id,),
            ).fetchall()
            interaction_count = db.execute(
                """
                SELECT COUNT(*) FROM drug_interactions
                WHERE drug1_id = ? OR drug2_id = ?
                """,
                (drug_id, drug_id),
            ).fetchone()[0]

        return {
            "drug": row_to_drug(drug),
            "categories": [row["category"] for row in categories],
            "foodInteractions": [row["description"] for row in food],
            "targets": [
                {
                    "name": row["name"],
                    "organism": row["organism"],
                    "action": row["action"],
                }
                for row in targets
            ],
            "interactionCount": interaction_count,
        }

    def drug_interactions(self, drug_id: str, query: str) -> dict:
        q = " ".join(query.strip().split())
        values: list[str] = [drug_id, drug_id]
        name_filter = ""
        if q:
            name_filter = "AND other.name LIKE ?"
            values.append(f"%{q}%")

        with get_db() as db:
            rows = db.execute(
                f"""
                WITH paired AS (
                    SELECT drug2_id AS other_id, description
                    FROM drug_interactions
                    WHERE drug1_id = ?
                    UNION
                    SELECT drug1_id AS other_id, description
                    FROM drug_interactions
                    WHERE drug2_id = ?
                )
                SELECT DISTINCT
                    other.drugbank_id AS id,
                    other.name AS name,
                    paired.description AS description
                FROM paired
                JOIN drugs other ON other.drugbank_id = paired.other_id
                WHERE 1 = 1
                {name_filter}
                ORDER BY other.name
                LIMIT 50
                """,
                values,
            ).fetchall()

        return {
            "results": [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": clean_text(row["description"]),
                    "severity": severity_for(row["description"])[0],
                    "label": severity_for(row["description"])[1],
                }
                for row in rows
            ]
        }


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")

    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), NeuroPharmHandler)
    print(f"NeuroPharmDB running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
