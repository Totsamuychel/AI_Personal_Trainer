from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime

Base = declarative_base()

class GoalType(enum.Enum):
    strength    = "strength"
    hypertrophy = "hypertrophy"
    fat_loss    = "fat_loss"
    endurance   = "endurance"

class WeekType(enum.Enum):
    strength    = "strength"     # 4-6 повторов, 85-90% 1RM
    hypertrophy = "hypertrophy"  # 8-12 повторов, 70-75% 1RM
    volume      = "volume"       # 12-15 повторов, 60-65% 1RM
    deload      = "deload"       # 10-12 повторов, 50% 1RM

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True)
    telegram_id     = Column(String, unique=True, nullable=False)
    name            = Column(String)
    age             = Column(Integer)
    height_cm       = Column(Float)
    weight_kg       = Column(Float)
    goal            = Column(Enum(GoalType))
    level           = Column(String)           # beginner / intermediate / advanced
    preferred_split = Column(String)           # PPL / Upper-Lower / Full Body
    injuries        = Column(JSON, default=[]) # ["боль в колене", ...]
    created_at      = Column(DateTime, default=datetime.utcnow)
    
    workouts        = relationship("WorkoutSession", back_populates="user")
    plans           = relationship("WeeklyPlan", back_populates="user")
    nutrition_logs  = relationship("NutritionLog", back_populates="user")

class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"))
    date         = Column(DateTime, default=datetime.utcnow)
    workout_type = Column(String)              # Push / Pull / Legs / Full Body
    week_type    = Column(Enum(WeekType))
    duration_min = Column(Integer)
    notes        = Column(String)
    
    user         = relationship("User", back_populates="workouts")
    exercises    = relationship("ExerciseLog", back_populates="session")

class ExerciseLog(Base):
    __tablename__ = "exercise_logs"
    id         = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"))
    name       = Column(String)
    sets       = Column(Integer)
    reps       = Column(JSON)   # [5, 5, 4] — повторы в каждом подходе
    weight_kg  = Column(JSON)   # [80, 80, 77.5] — вес в каждом подходе
    rpe        = Column(Float)  # Rate of Perceived Exertion (1-10)
    notes      = Column(String)
    
    session    = relationship("WorkoutSession", back_populates="exercises")

class PersonalRecord(Base):
    __tablename__ = "personal_records"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"))
    exercise    = Column(String)
    weight_kg   = Column(Float)
    reps        = Column(Integer)
    one_rm_est  = Column(Float)  # Расчётный 1RM по формуле Epley
    date        = Column(DateTime, default=datetime.utcnow)

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"))
    week_number = Column(Integer)
    week_type   = Column(Enum(WeekType))
    start_date  = Column(DateTime)
    plan_data   = Column(JSON)   # Полный план в JSON
    is_active   = Column(Integer, default=1)
    
    user        = relationship("User", back_populates="plans")

class NutritionLog(Base):
    __tablename__ = "nutrition_logs"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"))
    date         = Column(DateTime, default=datetime.utcnow)
    meal_name    = Column(String)
    description  = Column(String)      # Исходный текст пользователя
    calories     = Column(Float)
    protein_g    = Column(Float)
    carbs_g      = Column(Float)
    fat_g        = Column(Float)
    
    user         = relationship("User", back_populates="nutrition_logs")
