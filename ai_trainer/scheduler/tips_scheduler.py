import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from loguru import logger
from ai_trainer.agent.trainer_agent import build_trainer_graph
from ai_trainer.db import database, crud

async def send_morning_tip(bot: Bot):
    """Fetch all users and send them a personalized morning tip using the AI agent."""
    logger.info("Running morning tips job...")
    
    try:
        async with database.db_session() as db:
            users = await crud.get_all_users(db)
            
            app = build_trainer_graph()
            
            for user in users:
                try:
                    # Request a morning tip from the agent
                    initial_state = {
                        "messages": ["Дай мне короткий совет на сегодня, основываясь на моем профиле и прогрессе."],
                        "user_id": str(user.telegram_id),
                        "profile": {},
                        "workout_history": [],
                        "personal_records": [],
                        "retrieved_context": "",
                        "current_plan": {},
                        "action_type": "tip"
                    }
                    
                    result = await app.ainvoke(initial_state)
                    
                    if result and "messages" in result and result["messages"]:
                        tip = result["messages"][-1].content
                        await bot.send_message(user.telegram_id, f"☀️ Доброе утро, {user.name}!\n\n{tip}")
                except Exception as e:
                    logger.error(f"Failed to send tip to user {user.telegram_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in morning tips job: {e}")

def setup_scheduler(bot: Bot):
    """Initialize and start the scheduler."""
    scheduler = AsyncIOScheduler()
    
    # Schedule morning tip at 8:00 AM
    scheduler.add_job(send_morning_tip, "cron", hour=8, minute=0, args=[bot])
    
    scheduler.start()
    logger.info("Scheduler started.")
    return scheduler
