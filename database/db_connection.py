import os
import uuid
from datetime import datetime
import hashlib, random

from sqlalchemy import create_engine, text, or_, and_
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base, User, Drug, NeuroEffect, DrugInteraction, DrugTimeline, AlertLog, AIInteractionSuggestion
)



# --- DB URL: use env if set, else SQLite file in /data ---
DB_URL = os.getenv("NEUROPHARMDB_DB_URL")
if not DB_URL:
    # default local sqlite
    DB_URL = "sqlite:///data/neuropharmdb.db"

engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)


# -------------------------
# AUTH
# -------------------------
def authenticate_user(user_id: str, email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.user_id == user_id,
            User.email == email
        ).first()

        if not user:
            return None

        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    finally:
        db.close()


# -------------------------
# USER CRUD
# -------------------------
def create_user(user_id, name, email, role="patient", **extra_fields):
    """
    Creates a user safely even if the User model doesn't have optional fields like age/medical_history.
    If a user_id or email already exists, it updates name/role (and optional fields if present).
    """
    db = SessionLocal()
    try:
        # Check existing by user_id or email
        existing = db.query(User).filter(
            or_(User.user_id == user_id, User.email == email)
        ).first()

        # Build payload only for columns that exist on the model
        def set_if_attr(obj, key, value):
            if value is None:
                return
            if hasattr(obj, key):
                setattr(obj, key, value)

        if existing:
            set_if_attr(existing, "name", name)
            set_if_attr(existing, "email", email)
            set_if_attr(existing, "role", role)
            for k, v in extra_fields.items():
                set_if_attr(existing, k, v)
            db.commit()
            return True

        u = User()
        set_if_attr(u, "user_id", user_id)
        set_if_attr(u, "name", name)
        set_if_attr(u, "email", email)
        set_if_attr(u, "role", role)

        for k, v in extra_fields.items():
            set_if_attr(u, k, v)

        db.add(u)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()



def list_users():
    db = SessionLocal()
    try:
        rows = db.query(User).all()
        out = []
        for r in rows:
            out.append({
                "user_id": getattr(r, "user_id", None),
                "name": getattr(r, "name", None),
                "email": getattr(r, "email", None),
                "role": getattr(r, "role", None),
                # These may NOT exist in your model — so use getattr safely
                "age": getattr(r, "age", None),
                "medical_history": getattr(r, "medical_history", None),
                "address": getattr(r, "address", None),
            })
        return out
    finally:
        db.close()


def create_user_with_role(user_id: str, name: str, email: str, role: str = "patient", age=None, medical_history=None):
    """Backward-compatible alias."""
    return create_user(user_id=user_id, name=name, email=email, role=role, age=age, medical_history=medical_history)


# -------------------------
# DRUG CRUD
# -------------------------
def create_drug(drug_id: str, name: str, drug_class: str = None, mechanism: str = None):
    db = SessionLocal()
    try:
        d = Drug(drug_id=drug_id, name=name, drug_class=drug_class, mechanism=mechanism)
        db.add(d)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def list_drugs():
    db = SessionLocal()
    try:
        rows = db.query(Drug).order_by(Drug.name).all()
        return [{"drug_id": r.drug_id, "name": r.name, "class": r.drug_class, "mechanism": r.mechanism} for r in rows]
    finally:
        db.close()

def get_drug_by_id(drug_id: str):
    db = SessionLocal()
    try:
        d = db.query(Drug).filter(Drug.drug_id == drug_id).first()
        if not d:
            return None
        return {
            "drug_id": d.drug_id,
            "name": d.name,
            "class": d.drug_class,
            "mechanism": d.mechanism
        }
    finally:
        db.close()


def delete_drug(drug_id: str):
    db = SessionLocal()
    try:
        d = db.query(Drug).filter(Drug.drug_id == drug_id).first()
        if not d:
            raise ValueError("Drug not found")
        db.delete(d)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# -------------------------
# NEURO EFFECT CRUD
# -------------------------
def create_neuro_effect(effect_id, effect_name, category=None, severity_level=None, default_severity=None, **extra):
    """
    Creates a NeuroEffect without breaking if model doesn't have severity_level.
    If model has default_severity, we map severity_level -> default_severity.
    """
    db = SessionLocal()
    try:
        existing = db.query(NeuroEffect).filter(NeuroEffect.effect_id == effect_id).first()

        def set_if_attr(obj, key, value):
            if value is None:
                return
            if hasattr(obj, key):
                setattr(obj, key, value)

        # map string severity to numeric if needed
        sev_map = {"low": 3.5, "medium": 6.0, "high": 8.5}

        if default_severity is None and severity_level is not None:
            if isinstance(severity_level, str):
                default_severity = sev_map.get(severity_level.strip().lower(), 6.0)
            else:
                # if numeric is passed by mistake
                default_severity = float(severity_level)

        obj = existing if existing else NeuroEffect()

        set_if_attr(obj, "effect_id", effect_id)
        set_if_attr(obj, "effect_name", effect_name)

        # some schemas use "category"
        set_if_attr(obj, "category", category)

        # some schemas use "default_severity" instead
        set_if_attr(obj, "default_severity", default_severity)

        # if your model actually has severity_level, set it too (won't crash)
        set_if_attr(obj, "severity_level", severity_level)

        if not existing:
            db.add(obj)

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_neuro_effects():
    db = SessionLocal()
    try:
        rows = db.query(NeuroEffect).all()

        def sev_to_level(x):
            if x is None:
                return None
            try:
                v = float(x)
            except Exception:
                return None
            if v >= 8.0:
                return "High"
            if v >= 5.0:
                return "Medium"
            return "Low"

        out = []
        for r in rows:
            # Some schemas have severity_level (string), some have default_severity (float), some have neither.
            severity_level = getattr(r, "severity_level", None)

            default_severity = getattr(r, "default_severity", None)
            if severity_level is None:
                # If we only have numeric severity, convert to High/Medium/Low
                severity_level = sev_to_level(default_severity)

            out.append({
                "effect_id": getattr(r, "effect_id", None),
                "effect_name": getattr(r, "effect_name", None),
                "category": getattr(r, "category", None),
                # keep existing API key so frontend doesn't break
                "severity_level": severity_level,
                # also return numeric if available (safe extra)
                "default_severity": default_severity,
            })
        return out
    finally:
        db.close()


# -------------------------
# INTERACTIONS + ALERTS
# -------------------------
def add_interaction(interaction_id, drug1_id, drug2_id, effect_id, severity_score, mechanism="", evidence_level="moderate"):
    db = SessionLocal()
    try:
        existing = db.query(DrugInteraction).filter(DrugInteraction.interaction_id == interaction_id).first()
        if existing:
            existing.drug1_id = drug1_id
            existing.drug2_id = drug2_id
            existing.effect_id = effect_id
            existing.severity_score = float(severity_score)
            existing.mechanism = mechanism
            existing.evidence_level = evidence_level
        else:
            db.add(DrugInteraction(
                interaction_id=interaction_id,
                drug1_id=drug1_id,
                drug2_id=drug2_id,
                effect_id=effect_id,
                severity_score=float(severity_score),
                mechanism=mechanism,
                evidence_level=evidence_level
            ))
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_interactions():
    db = SessionLocal()
    try:
        q = db.query(DrugInteraction)

        # Order safely: if created_at exists use it, else fallback to interaction_id
        if hasattr(DrugInteraction, "created_at"):
            q = q.order_by(DrugInteraction.created_at.desc())
        elif hasattr(DrugInteraction, "interaction_id"):
            q = q.order_by(DrugInteraction.interaction_id.asc())

        rows = q.all()

        out = []
        for r in rows:
            out.append({
                "interaction_id": getattr(r, "interaction_id", None),
                "drug1_id": getattr(r, "drug1_id", None),
                "drug2_id": getattr(r, "drug2_id", None),
                "effect_id": getattr(r, "effect_id", None),
                "severity_score": float(getattr(r, "severity_score", 0.0) or 0.0),
                "mechanism": getattr(r, "mechanism", None),
                "evidence_level": getattr(r, "evidence_level", None),
            })

            # If your model ever adds created_at later, expose it (optional)
            if hasattr(r, "created_at"):
                out[-1]["created_at"] = getattr(r, "created_at")

        return out
    finally:
        db.close()


def create_interaction(interaction_id, drug1_id, drug2_id, effect_id, severity_score, mechanism="", evidence_level=""):
    db = SessionLocal()
    try:
        existing = db.query(DrugInteraction).filter(DrugInteraction.interaction_id == interaction_id).first()
        if existing:
            existing.drug1_id = drug1_id
            existing.drug2_id = drug2_id
            existing.effect_id = effect_id
            existing.severity_score = float(severity_score)
            existing.mechanism = mechanism
            existing.evidence_level = evidence_level
        else:
            db.add(DrugInteraction(
                interaction_id=interaction_id,
                drug1_id=drug1_id,
                drug2_id=drug2_id,
                effect_id=effect_id,
                severity_score=float(severity_score),
                mechanism=mechanism,
                evidence_level=evidence_level
            ))
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_interaction(interaction_id: str):
    db = SessionLocal()
    try:
        row = db.query(DrugInteraction).filter(DrugInteraction.interaction_id == interaction_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Stored-procedure equivalent (SQLite-friendly): top-risk combinations
def top_risk_combinations(limit: int = 10):
    db = SessionLocal()
    try:
        rows = db.query(DrugInteraction).order_by(DrugInteraction.severity_score.desc()).limit(limit).all()
        return [{
            "interaction_id": r.interaction_id,
            "drug1_id": r.drug1_id,
            "drug2_id": r.drug2_id,
            "effect_id": r.effect_id,
            "severity_score": r.severity_score,
            "mechanism": r.mechanism,
        } for r in rows]
    finally:
        db.close()


# -------------------------
# TIMELINE / HISTORY
# -------------------------
def add_timeline_entry(timeline_id: str, user_id: str, drug_id: str, dosage: str = None,
                       frequency: str = None, start_date: str = None, end_date: str = None, time_of_day: str = None):
    db = SessionLocal()
    try:
        t = DrugTimeline(
            timeline_id=timeline_id,
            user_id=user_id,
            drug_id=drug_id,
            dosage=dosage,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            time_of_day=time_of_day,
        )
        db.add(t)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def list_timeline_for_user(user_id: str):
    db = SessionLocal()
    try:
        rows = db.query(DrugTimeline).filter(DrugTimeline.user_id == user_id).all()
        return [{
            "timeline_id": r.timeline_id,
            "user_id": r.user_id,
            "drug_id": r.drug_id,
            "dosage": r.dosage,
            "frequency": r.frequency,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "time_of_day": r.time_of_day,
        } for r in rows]
    finally:
        db.close()


# =========================
# ALERTS / INTERACTIONS LOGIC
# =========================

def get_active_drugs_for_user(user_id: str):
    """Return unique drug_ids currently in user's timeline."""
    db = SessionLocal()
    try:
        rows = db.query(DrugTimeline.drug_id).filter(
            DrugTimeline.user_id == user_id
        ).all()
        return sorted({r[0] for r in rows if r and r[0]})
    finally:
        db.close()


def find_interaction_between(drug_a: str, drug_b: str):
    """Return interaction details if exists (order-independent)."""
    db = SessionLocal()
    try:
        inter = db.query(DrugInteraction).filter(
            or_(
                and_(DrugInteraction.drug1_id == drug_a, DrugInteraction.drug2_id == drug_b),
                and_(DrugInteraction.drug1_id == drug_b, DrugInteraction.drug2_id == drug_a),
            )
        ).first()

        if not inter:
            return None

        effect = db.query(NeuroEffect).filter(
            NeuroEffect.effect_id == inter.effect_id
        ).first()

        return {
            "interaction_id": inter.interaction_id,
            "drug1_id": inter.drug1_id,
            "drug2_id": inter.drug2_id,
            "effect_id": inter.effect_id,
            "effect_name": effect.effect_name if effect else inter.effect_id,
            "severity_score": float(inter.severity_score),
            "mechanism": inter.mechanism,
        }
    finally:
        db.close()

def create_alert_for_user(user_id, interaction_id=None, message=None, status="unread", **kwargs):
    db = SessionLocal()
    try:
        if not user_id or not message:
            raise ValueError("create_alert_for_user requires user_id and message")

        alert = AlertLog(
            alert_id=f"AL{uuid.uuid4().hex[:8].upper()}",
            user_id=user_id,
            interaction_id=interaction_id,
            message=message,
            status=status,
            created_at=datetime.utcnow(),
        )

        # Only set these if they exist in your AlertLog model
        if hasattr(AlertLog, "drug1_id"):
            setattr(alert, "drug1_id", kwargs.get("drug1_id") or kwargs.get("drug_a"))
        if hasattr(AlertLog, "drug2_id"):
            setattr(alert, "drug2_id", kwargs.get("drug2_id") or kwargs.get("drug_b"))

        db.add(alert)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_new_drug_and_alert(user_id: str, new_drug_id: str, min_severity: float = 7.0):
    """
    Called when user adds a drug to timeline.
    Checks interaction with existing drugs and creates alerts.
    """
    existing_drugs = get_active_drugs_for_user(user_id)
    existing_drugs = [d for d in existing_drugs if d != new_drug_id]

    alerts_created = 0

    for other_drug in existing_drugs:
        inter = find_interaction_between(new_drug_id, other_drug)
        if not inter:
            continue

        if inter["severity_score"] < min_severity:
            continue

        # Avoid duplicate unread alerts
        db = SessionLocal()
        try:
            exists = db.query(AlertLog).filter(
                AlertLog.user_id == user_id,
                AlertLog.interaction_id == inter["interaction_id"],
                AlertLog.status == "unread"
            ).first()
        finally:
            db.close()

        if exists:
            continue

        # Build a nicer message using drug names
        db2 = SessionLocal()
        try:
            d_new = db2.query(Drug).filter(Drug.drug_id == new_drug_id).first()
            d_other = db2.query(Drug).filter(Drug.drug_id == other_drug).first()
            new_name = d_new.name if d_new else new_drug_id
            other_name = d_other.name if d_other else other_drug
        finally:
            db2.close()

        msg = (
            f"Drug Interaction Detected: "
            f"{new_name} + {other_name} → {inter['effect_name']} "
            f"(Severity {inter['severity_score']}/10)."
        )
        if inter["mechanism"]:
            msg += f" Mechanism: {inter['mechanism']}"

        create_alert_for_user(
            user_id=user_id,
            interaction_id=inter["interaction_id"],
            drug1_id=new_drug_id,
            drug2_id=other_drug,
            message=msg
        )
        alerts_created += 1

    return alerts_created


def check_all_pairs_and_alert(user_id: str, min_severity: float = 7.0):
    """
    Patient feature: If user has multiple active drugs, check every pair and create alerts.
    Useful after bulk timeline updates.
    """
    drugs = get_active_drugs_for_user(user_id)
    high_pairs = 0
    for i in range(len(drugs)):
        for j in range(i + 1, len(drugs)):
            result = evaluate_pair_and_alert(user_id, drugs[i], drugs[j], threshold=min_severity)
            if result.get("status") == "high":
                high_pairs += 1
    # returns number of *high-risk pairs detected* (alerts are de-duplicated inside evaluate_pair_and_alert)
    return high_pairs
# =========================
# NOTIFICATIONS API (used by layout + alerts page)
# =========================

def count_unread_alerts_for_user(user_id: str) -> int:
    db = SessionLocal()
    try:
        return (
            db.query(AlertLog)
            .filter(AlertLog.user_id == user_id, AlertLog.status == "unread")
            .count()
        )
    finally:
        db.close()



def list_recent_alerts(user_id: str, limit: int = 10):
    db = SessionLocal()
    try:
        q = db.query(AlertLog).filter(AlertLog.user_id == user_id)

        # Safe ordering
        if hasattr(AlertLog, "created_at"):
            q = q.order_by(AlertLog.created_at.desc())

        rows = q.limit(int(limit)).all()

        out = []
        for a in rows:
            item = {
                "alert_id": getattr(a, "alert_id", None),
                "user_id": getattr(a, "user_id", None),
                "interaction_id": getattr(a, "interaction_id", None),
                "message": getattr(a, "message", ""),
                "status": getattr(a, "status", "unread"),
                "created_at": getattr(a, "created_at", None),
            }

            # These columns may not exist in your AlertLog model — add only if present
            if hasattr(a, "drug1_id"):
                item["drug1_id"] = getattr(a, "drug1_id", None)
            if hasattr(a, "drug2_id"):
                item["drug2_id"] = getattr(a, "drug2_id", None)

            out.append(item)

        return out
    finally:
        db.close()



def mark_alerts_read_for_user(user_id: str):
    db = SessionLocal()
    try:
        db.query(AlertLog).filter(
            AlertLog.user_id == user_id,
            AlertLog.status == "unread"
        ).update({"status": "read"}, synchronize_session=False)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_alert_explanation(alert_id: str):
    """
    Returns a structured explanation for an alert WITHOUT assuming AlertLog has drug1_id/drug2_id.
    Priority:
      1) If alert.interaction_id starts with 'AI-' -> use AIInteractionSuggestion
      2) Else if alert.interaction_id matches a DrugInteraction -> use DrugInteraction
      3) Else fallback to alert.message only
    """
    db = SessionLocal()
    try:
        a = db.query(AlertLog).filter(AlertLog.alert_id == alert_id).first()
        if not a:
            return {"title": "Alert not found", "details": ""}

        interaction_id = getattr(a, "interaction_id", None)
        message = getattr(a, "message", "") or ""
        created_at = getattr(a, "created_at", None)
        status = getattr(a, "status", None)

        # -------------------------
        # Case 1: AI-based alert
        # interaction_id like "AI-123"
        # -------------------------
        if isinstance(interaction_id, str) and interaction_id.startswith("AI-"):
            sid_str = interaction_id.split("-", 1)[1].strip()
            sid = None
            try:
                sid = int(sid_str)
            except Exception:
                sid = None

            if sid is not None:
                s = db.query(AIInteractionSuggestion).filter(
                    AIInteractionSuggestion.suggestion_id == sid
                ).first()

                if s:
                    d1 = db.query(Drug).filter(Drug.drug_id == s.drug1_id).first()
                    d2 = db.query(Drug).filter(Drug.drug_id == s.drug2_id).first()

                    title = "AI interaction suggestion"
                    ai_status = getattr(s, "status", "PENDING")
                    doctor_id = getattr(s, "doctor_id", None)
                    reviewed_at = getattr(s, "reviewed_at", None)

                    # Clear doctor decision string
                    decision_text = "Pending doctor review"
                    if ai_status == "APPROVED":
                        decision_text = "Doctor approved this AI suggestion"
                    elif ai_status == "DENIED":
                        decision_text = "Doctor denied this AI suggestion"

                    return {
                        "title": title,
                        "is_ai": True,
                        "ai_status": ai_status,
                        "decision": decision_text,
                        "doctor_id": doctor_id,
                        "reviewed_at": reviewed_at,
                        "created_at": created_at,
                        "status": status,
                        "drug_a": f"{d1.name} ({d1.drug_id})" if d1 else s.drug1_id,
                        "drug_b": f"{d2.name} ({d2.drug_id})" if d2 else s.drug2_id,
                        "predicted_effect": getattr(s, "predicted_effect", None),
                        "severity_score": float(getattr(s, "severity_score", 0.0) or 0.0),
                        "explanation": getattr(s, "explanation", "") or "",
                        "message": message,
                    }

        # -------------------------
        # Case 2: Known interaction alert
        # interaction_id like "I001"
        # -------------------------
        if interaction_id:
            it = db.query(DrugInteraction).filter(
                DrugInteraction.interaction_id == interaction_id
            ).first()

            if it:
                d1 = db.query(Drug).filter(Drug.drug_id == it.drug1_id).first()
                d2 = db.query(Drug).filter(Drug.drug_id == it.drug2_id).first()
                ef = db.query(NeuroEffect).filter(NeuroEffect.effect_id == it.effect_id).first()

                return {
                    "title": "Known drug interaction",
                    "is_ai": False,
                    "created_at": created_at,
                    "status": status,
                    "interaction_id": interaction_id,
                    "drug_a": f"{d1.name} ({d1.drug_id})" if d1 else it.drug1_id,
                    "drug_b": f"{d2.name} ({d2.drug_id})" if d2 else it.drug2_id,
                    "effect": getattr(ef, "effect_name", None) if ef else it.effect_id,
                    "severity_score": float(getattr(it, "severity_score", 0.0) or 0.0),
                    "mechanism": getattr(it, "mechanism", "") or "",
                    "evidence_level": getattr(it, "evidence_level", "") or "",
                    "message": message,
                }

        # -------------------------
        # Case 3: Fallback (no linkable interaction)
        # -------------------------
        return {
            "title": "Alert",
            "is_ai": False,
            "created_at": created_at,
            "status": status,
            "message": message,
            "details": "No linked interaction record was found for this alert.",
        }

    finally:
        db.close()

def run_sql_query(sql: str, allow_write: bool = False):
    """
    Runs raw SQL safely.
    - By default, allows only SELECT.
    - If allow_write=True, UPDATE/DELETE/DDL are allowed.
    Returns dict: {type, rows?, rowcount?}
    """
    if not sql or not sql.strip():
        raise ValueError("Empty SQL query")

    q = sql.strip().strip(";")
    q_lower = q.lower()

    is_select = q_lower.startswith("select") or q_lower.startswith("with")

    if not is_select and not allow_write:
        raise PermissionError("Only SELECT queries are allowed unless 'Allow write' is enabled.")

    db = SessionLocal()
    try:
        # Use the SQLAlchemy session connection
        conn = db.connection()
        res = conn.execute(text(q))

        if is_select:
            cols = res.keys()
            rows = [dict(zip(cols, r)) for r in res.fetchall()]
            return {"type": "select", "rows": rows}
        else:
            db.commit()
            return {"type": "write", "rowcount": res.rowcount if res.rowcount is not None else 0}

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def check_interaction_pair(drug_a: str, drug_b: str):
    """
    Returns interaction + effect + severity if exists, else None
    """
    db = SessionLocal()
    try:
        inter = db.query(DrugInteraction).filter(
            or_(
                and_(DrugInteraction.drug1_id == drug_a, DrugInteraction.drug2_id == drug_b),
                and_(DrugInteraction.drug1_id == drug_b, DrugInteraction.drug2_id == drug_a),
            )
        ).first()

        if not inter:
            return None

        eff = db.query(NeuroEffect).filter(NeuroEffect.effect_id == inter.effect_id).first()

        return {
            "interaction_id": inter.interaction_id,
            "drug1_id": inter.drug1_id,
            "drug2_id": inter.drug2_id,
            "effect_id": inter.effect_id,
            "effect_name": eff.effect_name if eff else inter.effect_id,
            "effect_category": eff.category if eff else None,
            "severity_score": float(inter.severity_score),
            "mechanism": inter.mechanism
        }
    finally:
        db.close()

def evaluate_pair_and_alert(user_id: str, drug_a: str, drug_b: str, threshold: float = 7.0):
    inter = check_interaction_pair(drug_a, drug_b)
    if not inter:
        return {"status": "safe", "interaction": None}

    # Decide risk
    sev = inter["severity_score"]
    risk = "high" if sev >= threshold else ("medium" if sev >= 4 else "low")

    if risk == "high":
        msg = (
            f"High-risk interaction: {drug_a} + {drug_b} → {inter['effect_name']} "
            f"(Severity {sev}/10)."
        )
        if inter.get("mechanism"):
            msg += f" Mechanism: {inter['mechanism']}"

        # de-dupe unread alerts for same interaction
        db = SessionLocal()
        try:
            dup = db.query(AlertLog).filter(
                AlertLog.user_id == user_id,
                AlertLog.interaction_id == inter["interaction_id"],
                AlertLog.status == "unread",
            ).first()
        finally:
            db.close()

        if not dup:
            create_alert_for_user(
                user_id=user_id,
                interaction_id=inter["interaction_id"],
                drug1_id=drug_a,
                drug2_id=drug_b,
                message=msg
            )

    return {"status": risk, "interaction": inter}

def get_session():
    """Helper for modules/IDE that expect get_session()."""
    return SessionLocal()


def ai_predict_effect(drug_a_id: str, drug_b_id: str):
    known = check_interaction_pair(drug_a_id, drug_b_id)
    if known:
        predicted_effect = known.get("effect_name") or "Interaction"
        base = float(known.get("severity_score", 6.0))
        explanation = known.get("mechanism") or "Based on known interaction in database."

        seed = int(hashlib.md5(f"{drug_a_id}|{drug_b_id}|{predicted_effect}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        jitter = rng.uniform(-0.7, 0.7)
        severity = max(0.0, min(10.0, base + jitter))

        return {
            "predicted_effect": predicted_effect,
            "severity_score": round(severity, 1),
            "explanation": explanation,
        }

    seed = int(hashlib.md5(f"{drug_a_id}|{drug_b_id}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    effects = ["Dizziness", "Sedation", "Seizures", "Weight Gain"]
    predicted_effect = rng.choice(effects)
    severity = rng.uniform(3.0, 9.5)

    explanation = "Prototype AI heuristic based on pattern simulation (not medical advice)."

    return {
        "predicted_effect": predicted_effect,
        "severity_score": round(severity, 1),
        "explanation": explanation,
    }


def store_ai_suggestion(user_id, drug1_id, drug2_id, predicted_effect, severity_score, explanation):
    db = SessionLocal()
    try:
        existing = db.query(AIInteractionSuggestion).filter(
            AIInteractionSuggestion.user_id == user_id,
            AIInteractionSuggestion.drug1_id == drug1_id,
            AIInteractionSuggestion.drug2_id == drug2_id,
            AIInteractionSuggestion.predicted_effect == predicted_effect,
            AIInteractionSuggestion.status == "PENDING"
        ).first()
        if existing:
            return existing.suggestion_id

        s = AIInteractionSuggestion(
            user_id=user_id,
            drug1_id=drug1_id,
            drug2_id=drug2_id,
            predicted_effect=predicted_effect,
            severity_score=float(severity_score),
            explanation=explanation,
            status="PENDING"
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s.suggestion_id
    finally:
        db.close()


def get_pending_ai_suggestions():
    db = SessionLocal()
    try:
        rows = db.query(AIInteractionSuggestion).filter(
            AIInteractionSuggestion.status == "PENDING"
        ).order_by(AIInteractionSuggestion.created_at.desc()).all()

        return [{
            "suggestion_id": r.suggestion_id,
            "user_id": r.user_id,
            "drug1_id": r.drug1_id,
            "drug2_id": r.drug2_id,
            "predicted_effect": r.predicted_effect,
            "severity_score": float(r.severity_score),
            "explanation": r.explanation,
            "created_at": r.created_at,
        } for r in rows]
    finally:
        db.close()


def approve_ai_suggestion(*args, **kwargs):
    suggestion_id = kwargs.pop("suggestion_id", None)
    approved = kwargs.pop("approved", None)
    doctor_id = kwargs.pop("doctor_id", None)

    if args:
        if suggestion_id is None and len(args) >= 1:
            suggestion_id = args[0]
        if approved is None and len(args) >= 2:
            approved = args[1]
        if doctor_id is None and len(args) >= 3:
            doctor_id = args[2]

    if suggestion_id is None or approved is None:
        raise TypeError("approve_ai_suggestion missing suggestion_id/approved")

    new_status = "APPROVED" if bool(approved) else "DENIED"

    db = SessionLocal()
    try:
        s = db.query(AIInteractionSuggestion).filter(
            AIInteractionSuggestion.suggestion_id == int(suggestion_id)
        ).first()
        if not s:
            raise ValueError("Suggestion not found")

        s.status = new_status
        s.doctor_id = doctor_id
        s.reviewed_at = datetime.utcnow()
        db.commit()

        msg = f"Doctor {new_status.lower()} AI suggestion for {s.drug1_id} + {s.drug2_id}: {s.predicted_effect} (Severity {float(s.severity_score)}/10)."

        create_alert_for_user(
            user_id=s.user_id,
            interaction_id=f"AI-{s.suggestion_id}",
            drug1_id=s.drug1_id,
            drug2_id=s.drug2_id,
            message=msg
        )
        return True
    finally:
        db.close()


def reject_ai_suggestion(*args, **kwargs):
    """Convenience wrapper used by the doctor UI."""
    if "approved" not in kwargs:
        kwargs["approved"] = False
    return approve_ai_suggestion(*args, **kwargs)