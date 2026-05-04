from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase
import enum
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class GoalType(enum.Enum):
    strength    = "strength"
    hypertrophy = "hypertrophy"
    fat_loss    = "fat_loss"
    endurance   = "endurance"

class WeekType(enum.Enum):
    strength    = "strength"     # 4-6 reps, 85-90% 1RM
    hypertrophy = "hypertrophy"  # 8-12 reps, 70-75% 1RM
    volume      = "volume"       # 12-15 reps, 60-65% 1RM
    deload      = "deload"       # 10-12 reps, 50% 1RM

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True)
    telegram_id     = Column(String, unique=True, nullable=False)
    name            = Column(String)
    language        = Column(String, default="ru") # ru / en
    age             = Column(Integer)
    height_cm       = Column(Float)
    weight_kg       = Column(Float)
    goal            = Column(Enum(GoalType))
    level           = Column(String)           # beginner / intermediate / advanced
    preferred_split = Column(String)           # PPL / Upper-Lower / Full Body
    injuries        = Column(JSON, default=list) # ["knee pain", ...]
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Scheduler settings
    morning_tip_enabled = Column(Boolean, default=True) # True - enabled, False - disabled
    morning_tip_time    = Column(String, default="08:00") # Format: HH:MM
    
    workouts        = relationship("WorkoutSession", back_populates="user", cascade="all, delete-orphan")
    plans           = relationship("WeeklyPlan", back_populates="user", cascade="all, delete-orphan")
    nutrition_logs  = relationship("NutritionLog", back_populates="user", cascade="all, delete-orphan")
    personal_records = relationship("PersonalRecord", back_populates="user", cascade="all, delete-orphan")

class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), index=True)
    date         = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    workout_type = Column(String)              # Push / Pull / Legs / Full Body
    week_type    = Column(Enum(WeekType))
    duration_min = Column(Integer)
    notes        = Column(String)
    
    user         = relationship("User", back_populates="workouts")
    exercises    = relationship("ExerciseLog", back_populates="session", cascade="all, delete-orphan")

class ExerciseLog(Base):
    __tablename__ = "exercise_logs"
    id         = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"), index=True)
    name       = Column(String, index=True)
    sets       = Column(Integer)
    reps       = Column(JSON)   # [5, 5, 4] — reps in each set
    weight_kg  = Column(JSON)   # [80, 80, 77.5] — weight in each set
    rpe        = Column(Float)  # Rate of Perceived Exertion (1-10)
    notes      = Column(String)
    
    session    = relationship("WorkoutSession", back_populates="exercises")

class PersonalRecord(Base):
    __tablename__ = "personal_records"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), index=True)
    exercise    = Column(String, index=True)
    weight_kg   = Column(Float)
    reps        = Column(Integer)
    one_rm_est  = Column(Float)  # Estimated 1RM using Epley formula
    date        = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user        = relationship("User", back_populates="personal_records")

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), index=True)
    week_number = Column(Integer)
    week_type   = Column(Enum(WeekType))
    start_date  = Column(DateTime)
    plan_data   = Column(JSON)   # Full plan in JSON
    is_active   = Column(Boolean, default=True)
    
    user        = relationship("User", back_populates="plans")

class NutritionLog(Base):
    __tablename__ = "nutrition_logs"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"), index=True)
    date         = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    meal_name    = Column(String)
    description  = Column(String)      # Original user text
    calories     = Column(Float)
    protein_g    = Column(Float)
    carbs_g      = Column(Float)
    fat_g        = Column(Float)
    
    user        = relationship("User", back_populates="nutrition_logs")

class SystemSettings(Base):
    __tablename__ = "system_settings"
    id              = Column(Integer, primary_key=True)
    llm_provider    = Column(String, default="ollama")  # ollama / openai
    ollama_base_url = Column(String, default="http://localhost:11434")
    ollama_model    = Column(String, default="gpt-oss:20b")
    openai_api_key  = Column(String)
    openai_model    = Column(String, default="gpt-4o-mini")
    embedding_model = Column(String, default="nomic-embed-text")
    updated_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
