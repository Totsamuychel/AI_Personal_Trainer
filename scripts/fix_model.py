
import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from ai_trainer.db import crud, database, models

async def check():
    async with database.db_session() as db:
        settings = await crud.get_system_settings(db)
        print(f"CURRENT_DB_MODEL: {settings.ollama_model}")
        
        # If it's llama3:latest, reset it to gpt-oss20b as requested before
        if settings.ollama_model == "llama3:latest":
            settings.ollama_model = "gpt-oss20b"
            await db.commit()
            print("RESET_MODEL: Updated model to gpt-oss20b")

if __name__ == "__main__":
    asyncio.run(check())
