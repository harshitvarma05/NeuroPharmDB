from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    user_id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    address = Column(String(200))
    role = Column(String(20), default="patient")  # patient / doctor / admin


class Drug(Base):
    __tablename__ = "drug"

    drug_id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    drug_class = Column(String(100))
    mechanism = Column(String(200))


class NeuroEffect(Base):
    __tablename__ = "neuro_effect"

    effect_id = Column(String(20), primary_key=True)
    effect_name = Column(String(100), nullable=False)
    category = Column(String(50))
    default_severity = Column(Float, default=5.0)


class DrugInteraction(Base):
    __tablename__ = "drug_interaction"

    interaction_id = Column(String(20), primary_key=True)
    drug1_id = Column(String(20), ForeignKey("drug.drug_id"), nullable=False)
    drug2_id = Column(String(20), ForeignKey("drug.drug_id"), nullable=False)
    effect_id = Column(String(20), ForeignKey("neuro_effect.effect_id"), nullable=False)
    severity_score = Column(Float, default=5.0)
    mechanism = Column(String(500))
    evidence_level = Column(String(50), default="moderate")


class DrugTimeline(Base):
    __tablename__ = "drug_timeline"

    timeline_id = Column(String(20), primary_key=True)
    user_id = Column(String(20), ForeignKey("user.user_id"), nullable=False)
    drug_id = Column(String(20), ForeignKey("drug.drug_id"), nullable=False)
    dosage = Column(String(50))
    frequency = Column(String(50))
    start_date = Column(String(20))


class AlertLog(Base):
    __tablename__ = "alert_log"

    alert_id = Column(String(20), primary_key=True)
    user_id = Column(String(20), ForeignKey("user.user_id"), nullable=False)
    interaction_id = Column(String(20), ForeignKey("drug_interaction.interaction_id"), nullable=True)
    message = Column(String(500), nullable=False)
    status = Column(String(20), default="unread")  # unread/read
    created_at = Column(DateTime, default=datetime.utcnow)


class AIInteractionSuggestion(Base):
    """Stores AI-assisted interaction suggestions pending doctor review."""

    __tablename__ = "ai_interaction_suggestions"

    suggestion_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), ForeignKey("user.user_id"), nullable=False)

    drug1_id = Column(String(20), ForeignKey("drug.drug_id"), nullable=False)
    drug2_id = Column(String(20), ForeignKey("drug.drug_id"), nullable=False)

    predicted_effect = Column(String(100), nullable=False)
    severity_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)

    status = Column(String(20), default="PENDING")  # PENDING/APPROVED/DENIED
    doctor_id = Column(String(20), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    target_doctor_id = Column(String(20), ForeignKey("user.user_id"), nullable=True)