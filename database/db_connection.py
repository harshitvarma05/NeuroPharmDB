import os
import uuid
from datetime import datetime

from sqlalchemy import create_engine, text, or_, and_
from sqlalchemy.orm import sessionmaker

from database.models import Base, User, Drug, NeuroEffect, DrugInteraction, DrugTimeline, AlertLog


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
def create_user(user_id, name, email, age, medical_history, role="patient"):
    db = SessionLocal()
    try:
        u = User(
            user_id=user_id,
            name=name,
            email=email,
            age=age,
            medical_history=medical_history,
            role=role
        )
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
        rows = db.query(User).order_by(User.user_id).all()
        return [{
            "user_id": r.user_id,
            "name": r.name,
            "email": r.email,
            "role": getattr(r, "role", "patient"),
            "age": r.age,
            "medical_history": r.medical_history,
        } for r in rows]
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
def create_neuro_effect(effect_id: str, effect_name: str, category: str = None, severity_level: str = None):
    db = SessionLocal()
    try:
        e = NeuroEffect(effect_id=effect_id, effect_name=effect_name, category=category, severity_level=severity_level)
        db.add(e)
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
        rows = db.query(NeuroEffect).order_by(NeuroEffect.effect_name).all()
        return [{"effect_id": r.effect_id, "effect_name": r.effect_name, "category": r.category, "severity_level": r.severity_level} for r in rows]
    finally:
        db.close()


# -------------------------
# INTERACTIONS + ALERTS
# -------------------------
def add_interaction(interaction_id: str, drug1_id: str, drug2_id: str, effect_id: str, severity_score: float, mechanism: str = None):
    """
    Adds interaction. Also auto-creates alert if severity_score >= 7 (severity-based trigger behavior from synopsis).
    """
    db = SessionLocal()
    try:
        # duplicate detection: same pair + same effect
        dup = db.query(DrugInteraction).filter(
            or_(
                (DrugInteraction.drug1_id == drug1_id) & (DrugInteraction.drug2_id == drug2_id),
                (DrugInteraction.drug1_id == drug2_id) & (DrugInteraction.drug2_id == drug1_id),
            ),
            DrugInteraction.effect_id == effect_id
        ).first()
        if dup:
            raise ValueError("Duplicate interaction exists for this drug pair and effect.")

        inter = DrugInteraction(
            interaction_id=interaction_id,
            drug1_id=drug1_id,
            drug2_id=drug2_id,
            effect_id=effect_id,
            severity_score=float(severity_score),
            mechanism=mechanism,
        )
        db.add(inter)
        db.commit()

        # severity-based alert: for all users (practically: we create alerts for each user to show notifications)
        if float(severity_score) >= 7.0:
            users = db.query(User).all()
            msg = f"High-risk interaction detected between {drug1_id} and {drug2_id} (severity {severity_score})."
            for u in users:
                db.add(AlertLog(
                    alert_id=f"A{u.user_id}_{interaction_id}",
                    user_id=u.user_id,
                    interaction_id=interaction_id,
                    drug1_id=drug1_id,
                    drug2_id=drug2_id,
                    message=msg,
                    status="unread",
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
        rows = db.query(DrugInteraction).order_by(DrugInteraction.created_at.desc()).all()
        return [{
            "interaction_id": r.interaction_id,
            "drug1_id": r.drug1_id,
            "drug2_id": r.drug2_id,
            "effect_id": r.effect_id,
            "severity_score": r.severity_score,
            "mechanism": r.mechanism,
            "created_at": r.created_at,
        } for r in rows]
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


def create_alert_for_user(
    user_id: str,
    interaction_id: str,
    drug1_id: str,
    drug2_id: str,
    message: str
):
    """Create unread alert entry."""
    db = SessionLocal()
    try:
        alert = AlertLog(
            alert_id=f"AL{uuid.uuid4().hex[:8].upper()}",
            user_id=user_id,
            interaction_id=interaction_id,
            drug1_id=drug1_id,
            drug2_id=drug2_id,
            message=message,
            status="unread",
            created_at=datetime.utcnow(),
        )
        db.add(alert)
        db.commit()
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
            f"⚠️ Drug Interaction Detected: "
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
        return db.query(AlertLog).filter(
            AlertLog.user_id == user_id,
            AlertLog.status == "unread"
        ).count()
    finally:
        db.close()


def list_recent_alerts(user_id: str, limit: int = 20):
    db = SessionLocal()
    try:
        rows = db.query(AlertLog).filter(
            AlertLog.user_id == user_id
        ).order_by(AlertLog.created_at.desc()).limit(limit).all()

        # Enrich alerts with interaction severity + effect_name for UI badges
        out = []
        for a in rows:
            severity = None
            effect_name = None

            if a.interaction_id:
                inter = db.query(DrugInteraction).filter(
                    DrugInteraction.interaction_id == a.interaction_id
                ).first()
                if inter:
                    severity = float(inter.severity_score)
                    eff = db.query(NeuroEffect).filter(NeuroEffect.effect_id == inter.effect_id).first()
                    effect_name = eff.effect_name if eff else inter.effect_id

            out.append({
                "alert_id": a.alert_id,
                "interaction_id": a.interaction_id,
                "drug1_id": a.drug1_id,
                "drug2_id": a.drug2_id,
                "effect": effect_name,
                "severity": severity,
                "message": a.message,
                "status": a.status,
                "created_at": a.created_at,
            })
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
    For 'Why was I alerted?' panel.
    Returns joined info: drugs, effect, severity, mechanism, etc.
    """
    db = SessionLocal()
    try:
        a = db.query(AlertLog).filter(AlertLog.alert_id == alert_id).first()
        if not a:
            return None

        d1 = db.query(Drug).filter(Drug.drug_id == a.drug1_id).first()
        d2 = db.query(Drug).filter(Drug.drug_id == a.drug2_id).first()

        inter = None
        effect = None
        if a.interaction_id:
            inter = db.query(DrugInteraction).filter(
                DrugInteraction.interaction_id == a.interaction_id
            ).first()
            if inter:
                effect = db.query(NeuroEffect).filter(
                    NeuroEffect.effect_id == inter.effect_id
                ).first()

        return {
            "alert_id": a.alert_id,
            "status": a.status,
            "created_at": a.created_at,
            "message": a.message,

            "drug1_id": a.drug1_id,
            "drug1_name": d1.name if d1 else a.drug1_id,
            "drug1_class": d1.drug_class if d1 else None,
            "drug1_mechanism": d1.mechanism if d1 else None,

            "drug2_id": a.drug2_id,
            "drug2_name": d2.name if d2 else a.drug2_id,
            "drug2_class": d2.drug_class if d2 else None,
            "drug2_mechanism": d2.mechanism if d2 else None,

            "interaction_id": a.interaction_id,
            "severity_score": float(inter.severity_score) if inter else None,
            "interaction_mechanism": inter.mechanism if inter else None,
            "effect_id": inter.effect_id if inter else None,
            "effect_name": effect.effect_name if effect else None,
            "effect_category": effect.category if effect else None,
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
            f"⚠️ High-risk interaction: {drug_a} + {drug_b} → {inter['effect_name']} "
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
