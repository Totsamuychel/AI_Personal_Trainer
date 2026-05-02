from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from ai_trainer.bot.keyboards.main_menu import get_main_menu

router = Router()

@router.message(F.text.in_(["🏋️ Тренировка", "🏋️ Workout"]))
async def menu_workout(message: types.Message, state: FSMContext):
    from ai_trainer.bot.handlers.workout import cmd_workout
    await cmd_workout(message, state)

@router.message(F.text.in_(["🍎 Питание", "🍎 Nutrition"]))
async def menu_nutrition(message: types.Message, state: FSMContext):
    from ai_trainer.bot.handlers.nutrition import cmd_nutrition
    await cmd_nutrition(message, state)

@router.message(F.text.in_(["📈 Прогресс", "📈 Progress"]))
async def menu_progress(message: types.Message, state: FSMContext):
    from ai_trainer.bot.handlers.progress import cmd_progress
    await cmd_progress(message, state)

@router.message(F.text.in_(["📅 План на неделю", "📅 Weekly Plan"]))
async def menu_plan(message: types.Message, state: FSMContext):
    from ai_trainer.bot.handlers.plan import cmd_plan
    await cmd_plan(message, state)

@router.message(F.text.in_(["🧠 Задать вопрос ИИ", "🧠 Ask AI"]))
async def menu_ask_ai(message: types.Message):
    await message.answer("Я слушаю! Задай любой вопрос о тренировках или питании.")

@router.message(F.text.in_(["⚙️ Настройки", "⚙️ Settings"]))
async def menu_settings(message: types.Message, state: FSMContext):
    from ai_trainer.bot.handlers.settings import cmd_settings
    await cmd_settings(message, state)

@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu())
