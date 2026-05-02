
import asyncio
import os

# Set environment variable BEFORE importing database module
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from ai_trainer.db import crud, database, models

async def create_test_data():
    async with database.db_session() as db:
        user_data = {
            "telegram_id": "123456789",
            "name": "Ivan Drago",
            "age": 30,
            "goal": models.GoalType.strength,
            "level": "intermediate"
        }
        user = await crud.create_user(db, user_data)
        print(f"Created user: {user.name} (ID: {user.id})")
        
        workout_data = {
            "workout_type": "Push",
            "duration_min": 45
        }
        exercises = [
            {
                "name": "Bench Press",
                "sets": 3,
                "reps": [5, 5, 5],
                "weight_kg": [100, 100, 100]
            }
        ]
        session = await crud.create_workout_session(db, user.id, workout_data, exercises)
        print(f"Created workout session: {session.workout_type} (ID: {session.id})")

if __name__ == "__main__":
    asyncio.run(create_test_data())
