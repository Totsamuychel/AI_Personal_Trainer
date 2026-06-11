from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ai_trainer.db import crud, database, models
from pydantic import BaseModel
from aiogram import Bot
import os

from ai_trainer.api.deps import verify_admin_api_key

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_api_key)],
)

# Reused Bot instance: a new Bot() opens a fresh aiohttp session each time, so we
# keep one for the app's lifetime and close it on shutdown (see app lifespan).
_bot: Optional[Bot] = None


def _get_bot() -> Bot:
    global _bot
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="TELEGRAM_TOKEN not configured")
    if _bot is None:
        _bot = Bot(token=token)
    return _bot


async def close_bot() -> None:
    """Close the shared Bot's session; call on application shutdown."""
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None


async def get_db():
    async with database.db_session() as session:
        yield session

class MessageRequest(BaseModel):
    text: str

class SettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    embedding_model: Optional[str] = None

def _serialize_user(u: models.User) -> dict:
    return {
        "id": u.id,
        "telegram_id": u.telegram_id,
        "name": u.name,
        "language": u.language,
        "age": u.age,
        "height_cm": u.height_cm,
        "weight_kg": u.weight_kg,
        "goal": u.goal.value if u.goal else None,
        "level": u.level,
        "preferred_split": u.preferred_split,
        "injuries": u.injuries or [],
        "morning_tip_enabled": u.morning_tip_enabled,
        "morning_tip_time": u.morning_tip_time,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _openai_key_mask(raw: Optional[str]) -> Tuple[Optional[str], bool]:
    if not raw or not str(raw).strip():
        return None, False
    k = str(raw).strip()
    tail = k[-4:] if len(k) > 4 else ""
    masked = ("•" * 8 + tail) if tail else "••••"
    return masked, True


def _serialize_settings(s: Optional[models.SystemSettings]) -> dict:
    if not s:
        return {}
    masked, configured = _openai_key_mask(s.openai_api_key)
    return {
        "id": s.id,
        "llm_provider": s.llm_provider,
        "ollama_base_url": s.ollama_base_url,
        "ollama_model": s.ollama_model,
        "openai_model": s.openai_model,
        "embedding_model": s.embedding_model,
        "openai_api_key_masked": masked,
        "openai_api_key_configured": configured,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }

@router.get("/users")
async def get_admin_users(db: AsyncSession = Depends(get_db)):
    users = await crud.get_all_users(db)
    return [_serialize_user(u) for u in users]

@router.post("/users/{telegram_id}/message")
async def send_user_message(telegram_id: str, request: MessageRequest):
    bot = _get_bot()
    try:
        await bot.send_message(chat_id=telegram_id, text=request.text)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.post("/broadcast")
async def broadcast_message(request: MessageRequest, db: AsyncSession = Depends(get_db)):
    bot = _get_bot()
    users = await crud.get_all_users(db)
    sent, failed = 0, 0
    for user in users:
        try:
            await bot.send_message(chat_id=user.telegram_id, text=request.text)
            sent += 1
        except Exception:
            failed += 1
    return {"sent": sent, "failed": failed}

@router.get("/settings")
async def get_admin_settings(db: AsyncSession = Depends(get_db)):
    settings = await crud.get_system_settings(db)
    return _serialize_settings(settings)

@router.put("/settings")
async def update_admin_settings(update_data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    data = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if "openai_api_key" in data and not str(data["openai_api_key"]).strip():
        del data["openai_api_key"]
    settings = await crud.update_system_settings(db, data)
    return _serialize_settings(settings)

@router.get("/users/{user_id}/stats")
async def get_user_stats(user_id: int, db: AsyncSession = Depends(get_db)):
    volume_history = await crud.get_volume_history(db, user_id, limit=30)
    return {"volume_history": volume_history}

@router.get("/users/{user_id}/nutrition")
async def get_user_nutrition(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.NutritionLog)
        .filter(models.NutritionLog.user_id == user_id)
        .order_by(models.NutritionLog.date.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "date": l.date.isoformat() if l.date else None,
            "meal_name": l.meal_name,
            "description": l.description,
            "calories": l.calories,
            "protein_g": l.protein_g,
            "carbs_g": l.carbs_g,
            "fat_g": l.fat_g,
        }
        for l in logs
    ]

@router.get("/users/{user_id}/records")
async def get_user_records(user_id: int, db: AsyncSession = Depends(get_db)):
    records = await crud.get_all_personal_records(db, user_id)
    return [
        {
            "exercise": r.exercise,
            "weight_kg": r.weight_kg,
            "reps": r.reps,
            "one_rm_est": r.one_rm_est,
            "date": r.date.isoformat() if r.date else None,
        }
        for r in records
    ]

@router.get("/users/{user_id}/workouts")
async def get_user_workouts(user_id: int, limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.WorkoutSession)
        .options(selectinload(models.WorkoutSession.exercises))
        .filter(models.WorkoutSession.user_id == user_id)
        .order_by(models.WorkoutSession.date.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "date": s.date.isoformat() if s.date else None,
            "workout_type": s.workout_type,
            "duration_min": s.duration_min,
            "notes": s.notes,
            "exercises": [
                {
                    "name": e.name,
                    "sets": e.sets,
                    "reps": e.reps,
                    "weight_kg": e.weight_kg,
                }
                for e in s.exercises
            ],
        }
        for s in sessions
    ]
