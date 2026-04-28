from sqlalchemy.orm import Session
from . import models
from datetime import datetime

# User operations
def get_user_by_telegram_id(db: Session, telegram_id: str):
    return db.query(models.User).filter(models.User.telegram_id == telegram_id).first()

def create_user(db: Session, user_data: dict):
    db_user = models.User(**user_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Workout operations
def create_workout_session(db: Session, user_id: int, workout_data: dict, exercises: list[dict]):
    db_session = models.WorkoutSession(
        user_id=user_id,
        date=workout_data.get('date', datetime.utcnow()),
        workout_type=workout_data.get('workout_type'),
        week_type=workout_data.get('week_type'),
        duration_min=workout_data.get('duration_min'),
        notes=workout_data.get('notes')
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
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
    return db_session

def get_workout_history(db: Session, user_id: int, limit: int = 10):
    return db.query(models.WorkoutSession).filter(
        models.WorkoutSession.user_id == user_id
    ).order_by(models.WorkoutSession.date.desc()).limit(limit).all()

# Personal Record operations
def update_personal_record(db: Session, user_id: int, exercise: str, weight: float, reps: int):
    # Epley formula: 1RM = weight * (1 + reps/30)
    one_rm = weight * (1 + reps / 30) if reps > 1 else weight
    
    db_pr = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        models.PersonalRecord.exercise == exercise
    ).first()
    
    if not db_pr or one_rm > db_pr.one_rm_est:
        if not db_pr:
            db_pr = models.PersonalRecord(
                user_id=user_id,
                exercise=exercise,
                weight_kg=weight,
                reps=reps,
                one_rm_est=one_rm,
                date=datetime.utcnow()
            )
            db.add(db_pr)
        else:
            db_pr.weight_kg = weight
            db_pr.reps = reps
            db_pr.one_rm_est = one_rm
            db_pr.date = datetime.utcnow()
        
        db.commit()
        db.refresh(db_pr)
    return db_pr

# Nutrition operations
def create_nutrition_log(db: Session, user_id: int, nutrition_data: dict):
    db_log = models.NutritionLog(user_id=user_id, **nutrition_data)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
