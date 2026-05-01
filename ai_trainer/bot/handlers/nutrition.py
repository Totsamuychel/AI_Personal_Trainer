from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from ai_trainer.db import crud, database
from datetime import datetime

router = Router()

class NutritionStates(StatesGroup):
    waiting_for_meal_name = State()
    waiting_for_description = State()

@router.message(F.text == "/nutrition")
async def cmd_nutrition(message: types.Message, state: FSMContext):
    """Starts the nutrition logging FSM."""
    await message.answer("🍏 Давай запишем прием пищи!\n\nКак назовем этот прием пищи? (Например: Завтрак, Обед, Перекус)")
    await state.set_state(NutritionStates.waiting_for_meal_name)

@router.message(NutritionStates.waiting_for_meal_name)
async def process_meal_name(message: types.Message, state: FSMContext):
    """Saves the meal name and asks for the description."""
    if not message.text:
        return
        
    await state.update_data(meal_name=message.text)
    await message.answer("Отлично! Теперь опиши, что именно ты съел (и примерный вес, если знаешь). Я сам посчитаю КБЖУ.\n\nПример: 150г куриной грудки, 100г вареной гречки и помидор.")
    await state.set_state(NutritionStates.waiting_for_description)

@router.message(NutritionStates.waiting_for_description)
async def process_meal_description(message: types.Message, state: FSMContext):
    """Processes the description, uses the AI agent to calculate macros, and saves it."""
    if not message.text:
        return
        
    description = message.text
    data = await state.get_data()
    meal_name = data.get("meal_name", "Прием пищи")
    
    await message.answer("⏳ Считаю КБЖУ... Подожди секунду.")
    
    telegram_id = str(message.from_user.id)
    
    # Send this directly to the agent to parse and save
    from ai_trainer.agent.trainer_agent import build_trainer_graph
    from langchain_core.messages import HumanMessage
    
    try:
        initial_state = {
            "messages": [HumanMessage(content=f"Я съел '{meal_name}': {description}. Посчитай КБЖУ и сохрани это в мой дневник питания.")],
            "user_id": telegram_id,
            "user_profile": {},
            "personal_records": [],
            "recent_workouts": [],
            "retrieved_context": "",
            "current_plan": {},
            "action_type": "nutrition"
        }
        
        app = build_trainer_graph()
        result = await app.ainvoke(initial_state)
        
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1]
            await message.answer(response.content)
        else:
            await message.answer("Извини, не смог посчитать КБЖУ.")
            
    except Exception as e:
        logger.error(f"Error in nutrition calculation: {e}")
        await message.answer("Произошла ошибка при расчете питания.")
        
    await state.clear()
