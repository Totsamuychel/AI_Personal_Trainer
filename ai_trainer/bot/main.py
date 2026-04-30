import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ai_trainer.bot.handlers import start, workout, agent
from ai_trainer.scheduler.tips_scheduler import setup_scheduler

load_dotenv()

async def main():
    # Setup logging
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    logger.info("Starting AI Personal Trainer Bot...")

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not found in environment variables")
        return

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(workout.router)
    dp.include_router(agent.router) # Fallback handler for AI agent

    # Setup scheduler
    scheduler = setup_scheduler(bot)

    # Start polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        scheduler.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
