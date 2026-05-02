from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, update
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

# --- Async Operations ---

# User operations
async def get_user_by_telegram_id(db: AsyncSession, telegram_id: str) -> Optional[models.User]:
    logger.debug(f"Fetching user by Telegram ID: {telegram_id}")
    result = await db.execute(select(models.User).filter(models.User.telegram_id == str(telegram_id)))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_data: dict) -> models.User:
    logger.info(f"Creating new user with telegram_id: {user_data.get('telegram_id')}")
    db_user = models.User(**user_data)
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
        logger.success(f"User created successfully: ID {db_user.id}")
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        await db.rollback()
        raise
    return db_user

async def update_user_scheduler_settings(db: AsyncSession, user_id: int, enabled: int, time: str) -> Optional[models.User]:
    logger.info(f"Updating scheduler settings for user_id: {user_id}, enabled: {enabled}, time: {time}")
    try:
        await db.execute(
            update(models.User)
            .where(models.User.id == user_id)
            .values(morning_tip_enabled=enabled, morning_tip_time=time)
        )
        await db.commit()
        result = await db.execute(select(models.User).where(models.User.id == user_id))
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Failed to update user scheduler settings: {e}")
        await db.rollback()
        raise

async def get_all_users(db: AsyncSession) -> List[models.User]:
    logger.debug("Fetching all users")
    result = await db.execute(select(models.User))
    return list(result.scalars().all())

# Workout operations
async def create_workout_session(db: AsyncSession, user_id: int, workout_data: dict, exercises: List[dict]) -> models.WorkoutSession:
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
        await db.flush()
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
        
        await db.commit()
        await db.refresh(db_session)
        logger.success(f"Workout session {db_session.id} created with {len(exercises)} exercises")
    except Exception as e:
        logger.error(f"Failed to create workout session: {e}")
        await db.rollback()
        raise
    
    return db_session

async def get_workout_history(db: AsyncSession, user_id: int, limit: int = 10) -> List[models.WorkoutSession]:
    logger.debug(f"Fetching workout history for user_id {user_id}, limit {limit}")
    result = await db.execute(
        select(models.WorkoutSession)
        .filter(models.WorkoutSession.user_id == user_id)
        .order_by(models.WorkoutSession.date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

# Progress / Analytics operations
async def get_exercise_progress(db: AsyncSession, user_id: int, exercise_name: str, limit: int = 50) -> List[models.ExerciseLog]:
    """Fetches exercise logs for a specific exercise, ordered by date (oldest first)."""
    logger.debug(f"Fetching exercise progress for user_id {user_id}, exercise: {exercise_name}")
    result = await db.execute(
        select(models.ExerciseLog)
        .join(models.WorkoutSession)
        .filter(
            models.WorkoutSession.user_id == user_id,
            models.ExerciseLog.name == exercise_name
        )
        .order_by(models.WorkoutSession.date.asc())
        .limit(limit)
    )
    return list(result.scalars().all())

async def get_exercise_progress_with_dates(db: AsyncSession, user_id: int, exercise_name: str, limit: int = 50) -> list:
    """Fetches exercise logs with their session dates for chart plotting."""
    logger.debug(f"Fetching exercise progress with dates for user_id {user_id}, exercise: {exercise_name}")
    from sqlalchemy import func
    result = await db.execute(
        select(
            models.WorkoutSession.date,
            models.ExerciseLog.name,
            models.ExerciseLog.sets,
            models.ExerciseLog.reps,
            models.ExerciseLog.weight_kg
        )
        .join(models.WorkoutSession)
        .filter(
            models.WorkoutSession.user_id == user_id,
            models.ExerciseLog.name == exercise_name
        )
        .order_by(models.WorkoutSession.date.asc())
        .limit(limit)
    )
    return list(result.all())

async def get_user_exercises(db: AsyncSession, user_id: int) -> List[str]:
    """Returns a list of unique exercise names for a user."""
    logger.debug(f"Fetching exercise list for user_id {user_id}")
    from sqlalchemy import distinct
    result = await db.execute(
        select(distinct(models.ExerciseLog.name))
        .join(models.WorkoutSession)
        .filter(models.WorkoutSession.user_id == user_id)
        .order_by(models.ExerciseLog.name)
    )
    return [row[0] for row in result.all()]

async def get_all_personal_records(db: AsyncSession, user_id: int) -> List[models.PersonalRecord]:
    """Returns all personal records for a user."""
    logger.debug(f"Fetching all personal records for user_id {user_id}")
    result = await db.execute(
        select(models.PersonalRecord)
        .filter(models.PersonalRecord.user_id == user_id)
        .order_by(models.PersonalRecord.exercise)
    )
    return list(result.scalars().all())

async def get_volume_history(db: AsyncSession, user_id: int, limit: int = 30) -> list:
    """Fetches workout sessions with total volume (sets * reps * weight) per session."""
    logger.debug(f"Fetching volume history for user_id {user_id}")
    result = await db.execute(
        select(models.WorkoutSession)
        .filter(models.WorkoutSession.user_id == user_id)
        .order_by(models.WorkoutSession.date.asc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    
    volume_data = []
    for session in sessions:
        # Eagerly load exercises
        ex_result = await db.execute(
            select(models.ExerciseLog)
            .filter(models.ExerciseLog.session_id == session.id)
        )
        exercises = ex_result.scalars().all()
        
        total_volume = 0
        for ex in exercises:
            reps_list = ex.reps if isinstance(ex.reps, list) else [0]
            weights_list = ex.weight_kg if isinstance(ex.weight_kg, list) else [0]
            for r, w in zip(reps_list, weights_list):
                total_volume += r * w
        
        volume_data.append({
            "date": session.date,
            "workout_type": session.workout_type,
            "total_volume": total_volume,
            "duration_min": session.duration_min
        })
    
    return volume_data

# Personal Record operations
async def update_personal_record(db: AsyncSession, user_id: int, exercise: str, weight: float, reps: int) -> models.PersonalRecord:
    one_rm = calculate_1rm(weight, reps)
    logger.debug(f"Checking PR for user {user_id}, exercise: {exercise}")
    
    result = await db.execute(
        select(models.PersonalRecord).filter(
            models.PersonalRecord.user_id == user_id,
            models.PersonalRecord.exercise == exercise
        )
    )
    db_pr = result.scalars().first()
    
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
        
        await db.commit()
        if db_pr:
            await db.refresh(db_pr)
    except Exception as e:
        logger.error(f"Failed to update personal record: {e}")
        await db.rollback()
        raise
    return db_pr

# Nutrition operations
async def create_nutrition_log(db: AsyncSession, user_id: int, nutrition_data: dict) -> models.NutritionLog:
    logger.info(f"Creating nutrition log for user_id: {user_id}, meal: {nutrition_data.get('meal_name')}")
    db_log = models.NutritionLog(user_id=user_id, **nutrition_data)
    db.add(db_log)
    try:
        await db.commit()
        await db.refresh(db_log)
        logger.success(f"Nutrition log {db_log.id} created successfully")
    except Exception as e:
        logger.error(f"Failed to create nutrition log: {e}")
        await db.rollback()
        raise
    return db_log

# Weekly Plan operations
async def get_active_weekly_plan(db: AsyncSession, user_id: int) -> Optional[models.WeeklyPlan]:
    logger.debug(f"Fetching active weekly plan for user_id {user_id}")
    result = await db.execute(
        select(models.WeeklyPlan)
        .where(models.WeeklyPlan.user_id == user_id, models.WeeklyPlan.is_active == 1)
        .order_by(models.WeeklyPlan.id.desc())
    )
    return result.scalars().first()

# System Settings operations
async def get_system_settings(db: AsyncSession) -> models.SystemSettings:
    import os
    result = await db.execute(select(models.SystemSettings))
    settings = result.scalars().first()
    
    if not settings:
        # Create default settings if not exists
        settings = models.SystemSettings(
            llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    return settings

async def update_system_settings(db: AsyncSession, settings_data: dict) -> models.SystemSettings:
    settings = await get_system_settings(db)
    
    for key, value in settings_data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
            
    await db.commit()
    await db.refresh(settings)
    return settings

# --- Sync Operations ---

def get_user_by_telegram_id_sync(db: Session, telegram_id: str) -> Optional[models.User]:
    logger.debug(f"Fetching user by Telegram ID (sync): {telegram_id}")
    return db.query(models.User).filter(models.User.telegram_id == str(telegram_id)).first()

def get_all_users_sync(db: Session) -> List[models.User]:
    logger.debug("Fetching all users (sync)")
    return db.query(models.User).all()

def create_workout_session_sync(db: Session, user_id: int, workout_data: dict, exercises: List[dict]) -> models.WorkoutSession:
    logger.info(f"Creating workout session (sync) for user_id: {user_id}, type: {workout_data.get('workout_type')}")
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
    except Exception as e:
        logger.error(f"Failed to create workout session (sync): {e}")
        db.rollback()
        raise
    return db_session

def update_personal_record_sync(db: Session, user_id: int, exercise: str, weight: float, reps: int) -> models.PersonalRecord:
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
    except Exception as e:
        logger.error(f"Failed to update personal record (sync): {e}")
        db.rollback()
        raise
    return db_pr

def get_workout_history_sync(db: Session, user_id: int, limit: int = 10) -> List[models.WorkoutSession]:
    return db.query(models.WorkoutSession).filter(
        models.WorkoutSession.user_id == user_id
    ).order_by(models.WorkoutSession.date.desc()).limit(limit).all()

def create_nutrition_log_sync(db: Session, user_id: int, nutrition_data: dict) -> models.NutritionLog:
    db_log = models.NutritionLog(user_id=user_id, **nutrition_data)
    db.add(db_log)
    try:
        db.commit()
        db.refresh(db_log)
    except Exception as e:
        logger.error(f"Failed to create nutrition log (sync): {e}")
        db.rollback()
        raise
    return db_log

