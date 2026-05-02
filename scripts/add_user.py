
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from ai_trainer.db import crud, database, models

async def add_user():
    async with database.db_session() as db:
        user_data = {
            "telegram_id": "889320292",
            "name": "User",
            "goal": models.GoalType.hypertrophy,
            "level": "intermediate"
        }
        user = await crud.create_user(db, user_data)
        print(f"User 889320292 added: ID {user.id}")

if __name__ == "__main__":
    asyncio.run(add_user())
