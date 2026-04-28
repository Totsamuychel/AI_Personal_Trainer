from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ai_trainer.db import crud, database
from loguru import logger

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_goal = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    
    db = next(database.get_db())
    user = crud.get_user_by_telegram_id(db, telegram_id)
    
    if user:
        await message.answer(f"Привет, {user.name}! С возвращением. Используй /workout чтобы начать тренировку.")
        await state.clear()
    else:
        await message.answer("Привет! Я твой AI тренер. Давай познакомимся. Как тебя зовут?")
        await state.set_state(RegistrationStates.waiting_for_name)

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegistrationStates.waiting_for_age)

@router.message(RegistrationStates.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи число.")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Какой у тебя рост (в см)?")
    await state.set_state(RegistrationStates.waiting_for_height)

@router.message(RegistrationStates.waiting_for_height)
async def process_height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text)
        await state.update_data(height_cm=height)
        await message.answer("Какой у тебя сейчас вес (в кг)?")
        await state.set_state(RegistrationStates.waiting_for_weight)
    except ValueError:
        await message.answer("Пожалуйста, введи число.")

@router.message(RegistrationStates.waiting_for_weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        await state.update_data(weight_kg=weight)
        await message.answer("Какая у тебя цель? (сила, гипертрофия, похудение)")
        await state.set_state(RegistrationStates.waiting_for_goal)
    except ValueError:
        await message.answer("Пожалуйста, введи число.")

@router.message(RegistrationStates.waiting_for_goal)
async def process_goal(message: types.Message, state: FSMContext):
    goal_map = {
        "сила": "strength",
        "гипертрофия": "hypertrophy",
        "похудение": "fat_loss"
    }
    user_goal = message.text.lower()
    if user_goal not in goal_map:
        await message.answer("Выбери из: сила, гипертрофия, похудение")
        return
    
    data = await state.get_data()
    data['goal'] = goal_map[user_goal]
    data['telegram_id'] = str(message.from_user.id)
    
    db = next(database.get_db())
    try:
        crud.create_user(db, data)
        await message.answer("Отлично! Профиль создан. Теперь ты можешь использовать /workout для записи тренировок.")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await message.answer("Произошла ошибка при создании профиля.")
    finally:
        await state.clear()
