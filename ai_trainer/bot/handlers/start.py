from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from ai_trainer.db import crud, database
from ai_trainer.sheets.client import SheetsClient
from loguru import logger

router = Router()
sheets = SheetsClient()

class RegistrationStates(StatesGroup):
    waiting_for_language = State()
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_goal = State()

# Validation constants
MIN_AGE, MAX_AGE = 12, 100
MIN_HEIGHT, MAX_HEIGHT = 100, 250
MIN_WEIGHT, MAX_WEIGHT = 30, 250

from ai_trainer.bot.keyboards.main_menu import get_main_menu

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, telegram_id)
    
    if user:
        welcome_text = "Привет, {}! С возвращением. Выбери действие в меню ниже."
        if user.language == "en":
            welcome_text = "Hello, {}! Welcome back. Choose an action from the menu below."
            
        await message.answer(
            welcome_text.format(user.name),
            reply_markup=get_main_menu(user.language)
        )
        # Ensure spreadsheet is ready
        sheets.setup_spreadsheet()
        await state.clear()
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="Русский 🇷🇺", callback_data="lang_ru")
        builder.button(text="English 🇺🇸", callback_data="lang_en")
        builder.adjust(2)
        
        await message.answer(
            "Привет! Выбери язык интерфейса / Choose your language:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(RegistrationStates.waiting_for_language)

@router.callback_query(RegistrationStates.waiting_for_language, F.data.startswith("lang_"))
async def process_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(language=lang)
    
    prompt = "Как тебя зовут?"
    if lang == "en":
        prompt = "What is your name?"
        
    await callback.message.edit_text(prompt)
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.answer()

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    if len(message.text) < 2 or len(message.text) > 50:
        error = "Пожалуйста, введи корректное имя (от 2 до 50 символов)."
        if lang == "en":
            error = "Please enter a valid name (2 to 50 characters)."
        await message.answer(error)
        return
        
    await state.update_data(name=message.text)
    
    prompt = "Сколько тебе лет?"
    if lang == "en":
        prompt = "How old are you?"
        
    await message.answer(prompt)
    await state.set_state(RegistrationStates.waiting_for_age)

@router.message(RegistrationStates.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    if not message.text.isdigit():
        error = "Пожалуйста, введи число."
        if lang == "en":
            error = "Please enter a number."
        await message.answer(error)
        return
    
    age = int(message.text)
    if not (MIN_AGE <= age <= MAX_AGE):
        error = f"Пожалуйста, введи реальный возраст (от {MIN_AGE} до {MAX_AGE} лет)."
        if lang == "en":
            error = f"Please enter a realistic age (from {MIN_AGE} to {MAX_AGE} years)."
        await message.answer(error)
        return

    await state.update_data(age=age)
    
    prompt = "Какой у тебя рост (в см)?"
    if lang == "en":
        prompt = "What is your height (in cm)?"
        
    await message.answer(prompt)
    await state.set_state(RegistrationStates.waiting_for_height)

@router.message(RegistrationStates.waiting_for_height)
async def process_height(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    try:
        height = float(message.text.replace(',', '.'))
        if not (MIN_HEIGHT <= height <= MAX_HEIGHT):
            error = f"Пожалуйста, введи реальный рост (от {MIN_HEIGHT} до {MAX_HEIGHT} см)."
            if lang == "en":
                error = f"Please enter a realistic height (from {MIN_HEIGHT} to {MAX_HEIGHT} cm)."
            await message.answer(error)
            return
            
        await state.update_data(height_cm=height)
        
        prompt = "Какой у тебя сейчас вес (в кг)?"
        if lang == "en":
            prompt = "What is your current weight (in kg)?"
            
        await message.answer(prompt)
        await state.set_state(RegistrationStates.waiting_for_weight)
    except ValueError:
        error = "Пожалуйста, введи число (например: 175 или 180.5)."
        if lang == "en":
            error = "Please enter a number (e.g., 175 or 180.5)."
        await message.answer(error)

@router.message(RegistrationStates.waiting_for_weight)
async def process_weight(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    try:
        weight = float(message.text.replace(',', '.'))
        if not (MIN_WEIGHT <= weight <= MAX_WEIGHT):
            error = f"Пожалуйста, введи реальный вес (от {MIN_WEIGHT} до {MAX_WEIGHT} кг)."
            if lang == "en":
                error = f"Please enter a realistic weight (from {MIN_WEIGHT} to {MAX_WEIGHT} kg)."
            await message.answer(error)
            return
            
        await state.update_data(weight_kg=weight)
        
        builder = InlineKeyboardBuilder()
        if lang == "ru":
            builder.button(text="💪 Сила", callback_data="goal_strength")
            builder.button(text="🏗️ Гипертрофия", callback_data="goal_hypertrophy")
            builder.button(text="📉 Похудение", callback_data="goal_fat_loss")
            prompt = "Какая у тебя цель?"
        else:
            builder.button(text="💪 Strength", callback_data="goal_strength")
            builder.button(text="🏗️ Hypertrophy", callback_data="goal_hypertrophy")
            builder.button(text="📉 Fat Loss", callback_data="goal_fat_loss")
            prompt = "What is your goal?"
            
        builder.adjust(1)
        
        await message.answer(prompt, reply_markup=builder.as_markup())
        await state.set_state(RegistrationStates.waiting_for_goal)
    except ValueError:
        error = "Пожалуйста, введи число (например: 75 или 82.5)."
        if lang == "en":
            error = "Please enter a number (e.g., 75 or 82.5)."
        await message.answer(error)

@router.callback_query(RegistrationStates.waiting_for_goal, F.data.startswith("goal_"))
async def process_goal_callback(callback: types.CallbackQuery, state: FSMContext):
    goal = callback.data.split("_")[1]
    
    data = await state.get_data()
    lang = data.get("language", "ru")
    data['goal'] = goal
    data['telegram_id'] = str(callback.from_user.id)
    
    try:
        async with database.db_session() as db:
            user = await crud.create_user(db, data)
        
        # Initialize Google Sheets
        sheets.setup_spreadsheet()
        
        # Text for feedback
        if lang == "ru":
            goals_text = {"strength": "Сила", "hypertrophy": "Гипертрофия", "fat_loss": "Похудение"}
            success_msg = f"Цель выбрана: {goals_text.get(goal)}\nОтлично! Профиль создан. Используй меню ниже для управления тренировками."
        else:
            goals_text = {"strength": "Strength", "hypertrophy": "Hypertrophy", "fat_loss": "Fat Loss"}
            success_msg = f"Goal selected: {goals_text.get(goal)}\nGreat! Profile created. Use the menu below to manage your training."
        
        await callback.message.edit_text(success_msg)
        await callback.message.answer("Меню активировано:", reply_markup=get_main_menu(lang))
        await callback.answer()
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        error_msg = "Произошла ошибка при создании профиля."
        if lang == "en":
            error_msg = "An error occurred while creating your profile."
        await callback.message.answer(error_msg)
    finally:
        await state.clear()

@router.message(RegistrationStates.waiting_for_goal)
async def process_goal_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    msg = "Пожалуйста, выбери цель, нажав на одну из кнопок выше."
    if lang == "en":
        msg = "Please select a goal by clicking one of the buttons above."
    await message.answer(msg)
