from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# --- User(user_id, name, age, medical_history) + email for login ---
class User(Base):
    __tablename__ = "user"

    user_id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)  # needed for user_id + email login
    age = Column(Integer, nullable=True)
    medical_history = Column(String(500), nullable=True)

    timelines = relationship("DrugTimeline", back_populates="user", cascade="all, delete-orphan")
    role = Column(String(20), nullable=False, default="patient")  # "admin" or "patient"



# --- Drug(drug_id, name, class, mechanism) ---
class Drug(Base):
    __tablename__ = "drug"

    drug_id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    drug_class = Column(String(255), nullable=True)
    mechanism = Column(String(500), nullable=True)

    timelines = relationship("DrugTimeline", back_populates="drug", cascade="all, delete-orphan")


# --- NeuroEffect(effect_id, effect_name, category, severity_level) ---
class NeuroEffect(Base):
    __tablename__ = "neuro_effect"

    effect_id = Column(String(50), primary_key=True)
    effect_name = Column(String(255), nullable=False)
    category = Column(String(255), nullable=True)
    severity_level = Column(String(50), nullable=True)


# --- DrugInteraction(interaction_id, drug1_id, drug2_id, effect_id, severity_score, mechanism) ---
class DrugInteraction(Base):
    __tablename__ = "drug_interaction"

    interaction_id = Column(String(50), primary_key=True)
    drug1_id = Column(String(50), ForeignKey("drug.drug_id"), nullable=False)
    drug2_id = Column(String(50), ForeignKey("drug.drug_id"), nullable=False)
    effect_id = Column(String(50), ForeignKey("neuro_effect.effect_id"), nullable=False)
    severity_score = Column(Float, nullable=False)
    mechanism = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# --- DrugTimeline(timeline_id, user_id, drug_id, dosage, frequency, start_date, end_date, time_of_day) ---
class DrugTimeline(Base):
    __tablename__ = "drug_timeline"

    timeline_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("user.user_id"), nullable=False)
    drug_id = Column(String(50), ForeignKey("drug.drug_id"), nullable=False)

    dosage = Column(String(100), nullable=True)
    frequency = Column(String(100), nullable=True)
    start_date = Column(String(25), nullable=True)
    end_date = Column(String(25), nullable=True)
    time_of_day = Column(String(50), nullable=True)

    user = relationship("User", back_populates="timelines")
    drug = relationship("Drug", back_populates="timelines")


# --- AlertLog(alert_id, drug1_id, drug2_id, message, created_at) + status + user_id for notifications UI ---
# Your diagram also shows Status, so we include it.
class AlertLog(Base):
    __tablename__ = "alert_log"

    alert_id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("user.user_id"), nullable=False)
    interaction_id = Column(String(50), nullable=True)

    drug1_id = Column(String(50), nullable=False)
    drug2_id = Column(String(50), nullable=False)

    message = Column(String(500), nullable=False)
    status = Column(String(20), default="unread")  # unread/read
    created_at = Column(DateTime, default=datetime.utcnow)

class AIInteractionSuggestion(Base):
    __tablename__ = "ai_interaction_suggestion"

    suggestion_id = Column(Integer, primary_key=True, autoincrement=True)
    drug1_id = Column(String(50), nullable=False)
    drug2_id = Column(String(50), nullable=False)

    predicted_effect = Column(String(255), nullable=False)
    predicted_severity = Column(Float, nullable=True)

    explanation = Column(Text, nullable=True)

    status = Column(String(20), nullable=False, default="pending")  # pending/approved/rejected
    created_at = Column(DateTime, default=datetime.utcnow)

