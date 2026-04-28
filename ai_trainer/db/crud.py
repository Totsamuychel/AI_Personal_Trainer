from sqlalchemy.orm import Session
from . import models
from datetime import datetime, timezone
from typing import List, Optional

# Helper for 1RM calculation
def calculate_1rm(weight: float, reps: int) -> float:
    """Epley formula: 1RM = weight * (1 + reps/30)"""
    if reps <= 0 or weight <= 0:
        return 0.0
    if reps == 1:
        return weight
    return round(weight * (1 + reps / 30.0), 2)

# User operations
def get_user_by_telegram_id(db: Session, telegram_id: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.telegram_id == str(telegram_id)).first()

def create_user(db: Session, user_data: dict) -> models.User:
    db_user = models.User(**user_data)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception:
        db.rollback()
        raise
    return db_user

# Workout operations
def create_workout_session(db: Session, user_id: int, workout_data: dict, exercises: List[dict]) -> models.WorkoutSession:
    db_session = models.WorkoutSession(
        user_id=user_id,
        date=workout_data.get('date', datetime.now(timezone.utc)),
        workout_type=workout_data.get('workout_type'),
        week_type=workout_data.get('week_type'),
        duration_min=workout_data.get('duration_min'),
        notes=workout_data.get('notes')
    )
    db.add(db_session)
    
    try:
        # We need to flush to get db_session.id
        db.flush()
        
        for ex in exercises:
            db_ex = models.ExerciseLog(
                session_id=db_session.id,
                name=ex.get('name'),
                sets=ex.get('sets'),
                reps=ex.get('reps'),
                weight_kg=ex.get('weight_kg'),
                rpe=ex.get('rpe'),
                notes=ex.get('notes')
            )
            db.add(db_ex)
        
        db.commit()
        db.refresh(db_session)
    except Exception:
        db.rollback()
        raise
    
    return db_session

def get_workout_history(db: Session, user_id: int, limit: int = 10) -> List[models.WorkoutSession]:
    return db.query(models.WorkoutSession).filter(
        models.WorkoutSession.user_id == user_id
    ).order_by(models.WorkoutSession.date.desc()).limit(limit).all()

# Personal Record operations
def update_personal_record(db: Session, user_id: int, exercise: str, weight: float, reps: int) -> models.PersonalRecord:
    one_rm = calculate_1rm(weight, reps)
    
    db_pr = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        models.PersonalRecord.exercise == exercise
    ).first()
    
    try:
        if not db_pr:
            db_pr = models.PersonalRecord(
                user_id=user_id,
                exercise=exercise,
                weight_kg=weight,
                reps=reps,
                one_rm_est=one_rm,
                date=datetime.now(timezone.utc)
            )
            db.add(db_pr)
        elif one_rm > db_pr.one_rm_est:
            db_pr.weight_kg = weight
            db_pr.reps = reps
            db_pr.one_rm_est = one_rm
            db_pr.date = datetime.now(timezone.utc)
        
        db.commit()
        if db_pr:
            db.refresh(db_pr)
    except Exception:
        db.rollback()
        raise
    return db_pr

# Nutrition operations
def create_nutrition_log(db: Session, user_id: int, nutrition_data: dict) -> models.NutritionLog:
    db_log = models.NutritionLog(user_id=user_id, **nutrition_data)
    db.add(db_log)
    try:
        db.commit()
        db.refresh(db_log)
    except Exception:
        db.rollback()
        raise
    return db_log
