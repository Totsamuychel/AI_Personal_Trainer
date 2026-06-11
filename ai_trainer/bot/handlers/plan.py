from aiogram import Router, types, F
from loguru import logger
from ai_trainer.db import crud, database
from ai_trainer.bot.utils import send_long_message
import json

router = Router()

@router.message(F.text == "/plan")
async def cmd_plan(message: types.Message):
    """Shows the current active weekly plan or triggers generation."""
    telegram_id = str(message.from_user.id)
    
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            await message.answer("Сначала зарегистрируйся с помощью /start")
            return
            
        plan = await crud.get_active_weekly_plan(db, user.id)
        
    if not plan:
        await message.answer("У тебя пока нет активного плана тренировок на эту неделю.\nНапиши мне 'Составь мне план на неделю', чтобы я сгенерировал его!")
        return
        
    try:
        plan_data = json.loads(plan.plan_data) if isinstance(plan.plan_data, str) else plan.plan_data
        
        text = f"📋 **План на неделю #{plan.week_number}**\n"
        text += f"Тип: {plan.week_type.value if hasattr(plan.week_type, 'value') else plan.week_type}\n\n"
        
        for day in plan_data.get("days", []):
            text += f"📅 **{day.get('day_name', 'День')}** - {day.get('focus', '')}\n"
            for ex in day.get("exercises", []):
                text += f"  • {ex.get('name')}: {ex.get('sets')}x{ex.get('reps')} ({ex.get('target_rpe', 'RPE 7-8')})\n"
            text += "\n"
            
        await send_long_message(message, text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error parsing plan: {e}")
        await message.answer("Произошла ошибка при отображении плана.")
