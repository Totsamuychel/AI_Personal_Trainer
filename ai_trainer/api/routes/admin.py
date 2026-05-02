from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ai_trainer.db import crud, database, models
from pydantic import BaseModel
from aiogram import Bot
import os

router = APIRouter(prefix="/admin", tags=["admin"])

# Dependency
async def get_db():
    async with database.db_session() as session:
        yield session

class MessageRequest(BaseModel):
    text: str

class SettingsUpdate(BaseModel):
    llm_provider: str = None
    ollama_base_url: str = None
    ollama_model: str = None
    openai_api_key: str = None
    openai_model: str = None
    embedding_model: str = None

@router.get("/users")
async def get_admin_users(db: AsyncSession = Depends(get_db)):
    users = await crud.get_all_users(db)
    return users

@router.post("/users/{telegram_id}/message")
async def send_user_message(telegram_id: str, request: MessageRequest):
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="TELEGRAM_TOKEN not configured")
    
    bot = Bot(token=token)
    try:
        await bot.send_message(chat_id=telegram_id, text=request.text)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
    finally:
        await bot.session.close()

@router.get("/settings")
async def get_admin_settings(db: AsyncSession = Depends(get_db)):
    settings = await crud.get_system_settings(db)
    return settings

@router.put("/settings")
async def update_admin_settings(update_data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    # Filter out None values
    data = {k: v for k, v in update_data.model_dump().items() if v is not None}
    settings = await crud.update_system_settings(db, data)
    return settings

@router.get("/users/{user_id}/stats")
async def get_user_stats(user_id: int, db: AsyncSession = Depends(get_db)):
    # Get volume history
    volume_history = await crud.get_volume_history(db, user_id, limit=30)
    return {
        "volume_history": volume_history
    }

@router.get("/users/{user_id}/nutrition")
async def get_user_nutrition(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.NutritionLog)
        .filter(models.NutritionLog.user_id == user_id)
        .order_by(models.NutritionLog.date.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return logs
