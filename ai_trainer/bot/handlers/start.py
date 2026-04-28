from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ai_trainer.db import crud, database
from loguru import logger

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_goal = State()

# Validation constants
MIN_AGE, MAX_AGE = 12, 100
MIN_HEIGHT, MAX_HEIGHT = 100, 250
MIN_WEIGHT, MAX_WEIGHT = 30, 250

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    
    with database.db_session() as db:
        user = crud.get_user_by_telegram_id(db, telegram_id)
    
    if user:
        await message.answer(f"Привет, {user.name}! С возвращением. Используй /workout чтобы начать тренировку.")
        await state.clear()
    else:
        await message.answer("Привет! Я твой AI тренер. Давай познакомимся. Как тебя зовут?")
        await state.set_state(RegistrationStates.waiting_for_name)

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) < 2 or len(message.text) > 50:
        await message.answer("Пожалуйста, введи корректное имя (от 2 до 50 символов).")
        return
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await state.set_state(RegistrationStates.waiting_for_age)

@router.message(RegistrationStates.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи число.")
        return
    
    age = int(message.text)
    if not (MIN_AGE <= age <= MAX_AGE):
        await message.answer(f"Пожалуйста, введи реальный возраст (от {MIN_AGE} до {MAX_AGE} лет).")
        return

    await state.update_data(age=age)
    await message.answer("Какой у тебя рост (в см)?")
    await state.set_state(RegistrationStates.waiting_for_height)

@router.message(RegistrationStates.waiting_for_height)
async def process_height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text.replace(',', '.'))
        if not (MIN_HEIGHT <= height <= MAX_HEIGHT):
            await message.answer(f"Пожалуйста, введи реальный рост (от {MIN_HEIGHT} до {MAX_HEIGHT} см).")
            return
            
        await state.update_data(height_cm=height)
        await message.answer("Какой у тебя сейчас вес (в кг)?")
        await state.set_state(RegistrationStates.waiting_for_weight)
    except ValueError:
        await message.answer("Пожалуйста, введи число (например: 175 или 180.5).")

@router.message(RegistrationStates.waiting_for_weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        if not (MIN_WEIGHT <= weight <= MAX_WEIGHT):
            await message.answer(f"Пожалуйста, введи реальный вес (от {MIN_WEIGHT} до {MAX_WEIGHT} кг).")
            return
            
        await state.update_data(weight_kg=weight)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="💪 Сила", callback_data="goal_strength")
        builder.button(text="🏗️ Гипертрофия", callback_data="goal_hypertrophy")
        builder.button(text="📉 Похудение", callback_data="goal_fat_loss")
        builder.adjust(1)
        
        await message.answer(
            "Какая у тебя цель?",
            reply_markup=builder.as_markup()
        )
        await state.set_state(RegistrationStates.waiting_for_goal)
    except ValueError:
        await message.answer("Пожалуйста, введи число (например: 75 или 82.5).")

@router.callback_query(RegistrationStates.waiting_for_goal, F.data.startswith("goal_"))
async def process_goal_callback(callback: types.CallbackQuery, state: FSMContext):
    goal = callback.data.split("_")[1]
    
    data = await state.get_data()
    data['goal'] = goal
    data['telegram_id'] = str(callback.from_user.id)
    
    try:
        with database.db_session() as db:
            crud.create_user(db, data)
        
        goals_text = {
            "strength": "Сила",
            "hypertrophy": "Гипертрофия",
            "fat_loss": "Похудение"
        }
        
        await callback.message.edit_text(f"Цель выбрана: {goals_text.get(goal)}\nОтлично! Профиль создан. Теперь ты можешь использовать /workout для записи тренировок.")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await callback.message.answer("Произошла ошибка при создании профиля.")
    finally:
        await state.clear()

@router.message(RegistrationStates.waiting_for_goal)
async def process_goal_text(message: types.Message):
    await message.answer("Пожалуйста, выбери цель, нажав на одну из кнопок выше.")
