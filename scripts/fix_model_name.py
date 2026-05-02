
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from ai_trainer.db import crud, database, models

async def fix():
    async with database.db_session() as db:
        settings = await crud.get_system_settings(db)
        print(f"OLD_MODEL: {settings.ollama_model}")
        settings.ollama_model = "gpt-oss:20b"
        await db.commit()
        print(f"NEW_MODEL: {settings.ollama_model}")

if __name__ == "__main__":
    asyncio.run(fix())
