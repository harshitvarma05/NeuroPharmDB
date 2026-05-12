from __future__ import annotations

import html
import json
import mimetypes
import os
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


def compact(text: str | None, limit: int = 500) -> str:
    if not text:
        return ""
    cleaned = " ".join(str(text).split())
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
        "description": compact(row["description"], 900),
        "indication": compact(row["indication"], 900),
        "mechanism": compact(row["mechanism_of_action"], 900),
        "toxicity": compact(row["toxicity"], 900),
        "metabolism": compact(row["metabolism"], 700),
        "half_life": compact(row["half_life"], 400),
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
            elif path == "/api/check":
                params = parse_qs(parsed.query)
                self.send_json(
                    self.check_pair(
                        params.get("drug1", [""])[0],
                        params.get("drug2", [""])[0],
                    )
                )
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
                LIMIT 18
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
                "description": interaction["description"],
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
                SELECT DISTINCT
                    other.drugbank_id AS id,
                    other.name AS name,
                    di.description AS description
                FROM drug_interactions di
                JOIN drugs other ON other.drugbank_id =
                    CASE WHEN di.drug1_id = ? THEN di.drug2_id ELSE di.drug1_id END
                WHERE (di.drug1_id = ? OR di.drug2_id = ?)
                {name_filter}
                ORDER BY other.name
                LIMIT 50
                """,
                [drug_id, *values],
            ).fetchall()

        return {
            "results": [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
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
