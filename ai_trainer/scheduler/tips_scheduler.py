import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from langchain_core.messages import HumanMessage
from loguru import logger
from ai_trainer.agent.trainer_agent import build_trainer_graph
from ai_trainer.bot.utils import normalize_content
from ai_trainer.db import database, crud
from datetime import datetime

async def send_morning_tip(bot: Bot):
    """Fetch all users and send them a personalized morning tip if their time has come."""
    now = datetime.now().strftime("%H:%M")
    logger.debug(f"Running morning tips check for time: {now}")

    try:
        async with database.db_session() as db:
            users = await crud.get_all_users(db)

            app = build_trainer_graph()

            for user in users:
                # Check if tips are enabled and if it's the right time
                if not user.morning_tip_enabled or user.morning_tip_time != now:
                    continue

                try:
                    logger.info(f"Sending morning tip to user {user.telegram_id}")
                    # Request a morning tip from the agent
                    initial_state = {
                        "messages": [HumanMessage(content="Дай мне короткий совет на сегодня, основываясь на моем профиле и прогрессе.")],
                        "user_id": str(user.telegram_id),
                        "user_profile": {},
                        "personal_records": [],
                        "recent_workouts": [],
                        "retrieved_context": "",
                        "user_memories": [],
                        "current_plan": {},
                        "action_type": "tip"
                    }

                    result = await app.ainvoke(initial_state)

                    if result and "messages" in result and result["messages"]:
                        tip = normalize_content(getattr(result["messages"][-1], "content", "")).strip()
                        if tip:
                            await bot.send_message(user.telegram_id, f"☀️ Доброе утро, {user.name}!\n\n{tip}")
                except Exception as e:
                    logger.error(f"Failed to send tip to user {user.telegram_id}: {e}")

    except Exception as e:
        logger.error(f"Error in morning tips job: {e}")

def setup_scheduler(bot: Bot):
    """Initialize and start the scheduler."""
    scheduler = AsyncIOScheduler()

    # Check every minute for users who should receive a tip
    scheduler.add_job(send_morning_tip, "cron", minute="*", args=[bot])

    scheduler.start()
    logger.info("Scheduler started (checking every minute).")
    return scheduler

