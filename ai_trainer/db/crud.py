from sqlalchemy.orm import Session
from . import models
from datetime import datetime, timezone
from typing import List, Optional
from loguru import logger

# Helper for 1RM calculation
def calculate_1rm(weight: float, reps: int) -> float:
    """Epley formula: 1RM = weight * (1 + reps/30)"""
    if reps <= 0 or weight <= 0:
        return 0.0
    if reps == 1:
        return weight
    res = round(weight * (1 + reps / 30.0), 2)
    logger.debug(f"Calculated 1RM: {weight}kg x {reps} reps -> {res}kg")
    return res

# User operations
def get_user_by_telegram_id(db: Session, telegram_id: str) -> Optional[models.User]:
    logger.debug(f"Fetching user by Telegram ID: {telegram_id}")
    return db.query(models.User).filter(models.User.telegram_id == str(telegram_id)).first()

def create_user(db: Session, user_data: dict) -> models.User:
    logger.info(f"Creating new user with telegram_id: {user_data.get('telegram_id')}")
    db_user = models.User(**user_data)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
        logger.success(f"User created successfully: ID {db_user.id}")
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        db.rollback()
        raise
    return db_user

# Workout operations
def create_workout_session(db: Session, user_id: int, workout_data: dict, exercises: List[dict]) -> models.WorkoutSession:
    logger.info(f"Creating workout session for user_id: {user_id}, type: {workout_data.get('workout_type')}")
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
        logger.debug(f"Workout session flushed, ID: {db_session.id}")
        
        for ex in exercises:
            logger.debug(f"Adding exercise log: {ex.get('name')}")
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
        logger.success(f"Workout session {db_session.id} created with {len(exercises)} exercises")
    except Exception as e:
        logger.error(f"Failed to create workout session: {e}")
        db.rollback()
        raise
    
    return db_session

def get_workout_history(db: Session, user_id: int, limit: int = 10) -> List[models.WorkoutSession]:
    logger.debug(f"Fetching workout history for user_id {user_id}, limit {limit}")
    return db.query(models.WorkoutSession).filter(
        models.WorkoutSession.user_id == user_id
    ).order_by(models.WorkoutSession.date.desc()).limit(limit).all()

# Personal Record operations
def update_personal_record(db: Session, user_id: int, exercise: str, weight: float, reps: int) -> models.PersonalRecord:
    one_rm = calculate_1rm(weight, reps)
    logger.debug(f"Checking PR for user {user_id}, exercise: {exercise}")
    
    db_pr = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        models.PersonalRecord.exercise == exercise
    ).first()
    
    try:
        if not db_pr:
            logger.info(f"New PR record for user {user_id}: {exercise}")
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
            logger.info(f"PR updated for user {user_id}: {exercise} ({db_pr.one_rm_est} -> {one_rm})")
            db_pr.weight_kg = weight
            db_pr.reps = reps
            db_pr.one_rm_est = one_rm
            db_pr.date = datetime.now(timezone.utc)
        
        db.commit()
        if db_pr:
            db.refresh(db_pr)
    except Exception as e:
        logger.error(f"Failed to update personal record: {e}")
        db.rollback()
        raise
    return db_pr

# Nutrition operations
def create_nutrition_log(db: Session, user_id: int, nutrition_data: dict) -> models.NutritionLog:
    logger.info(f"Creating nutrition log for user_id: {user_id}, meal: {nutrition_data.get('meal_name')}")
    db_log = models.NutritionLog(user_id=user_id, **nutrition_data)
    db.add(db_log)
    try:
        db.commit()
        db.refresh(db_log)
        logger.success(f"Nutrition log {db_log.id} created successfully")
    except Exception as e:
        logger.error(f"Failed to create nutrition log: {e}")
        db.rollback()
        raise
    return db_log
