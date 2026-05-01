from fastapi import FastAPI, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ai_trainer.db import crud, database

app = FastAPI(
    title="AI Personal Trainer API",
    description="REST API for the AI Personal Trainer application",
    version="1.0.0"
)

# Dependency
async def get_db():
    async with database.db_session() as session:
        yield session

@app.get("/")
async def root():
    return {"message": "Welcome to AI Personal Trainer API"}

@app.get("/api/users/{telegram_id}")
async def get_user(telegram_id: str, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": user.id,
        "name": user.name,
        "age": user.age,
        "goal": user.goal,
        "level": user.level,
        "preferred_split": user.preferred_split
    }

@app.get("/api/users/{telegram_id}/workouts")
async def get_user_workouts(telegram_id: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    workouts = await crud.get_workout_history(db, user.id, limit)
    return workouts

@app.get("/api/users/{telegram_id}/plan")
async def get_user_plan(telegram_id: str, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    plan = await crud.get_active_weekly_plan(db, user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found")
        
    import json
    plan_data = json.loads(plan.plan_data) if isinstance(plan.plan_data, str) else plan.plan_data
    return {
        "week_number": plan.week_number,
        "week_type": plan.week_type.value if hasattr(plan.week_type, 'value') else plan.week_type,
        "start_date": plan.start_date,
        "plan": plan_data
    }
