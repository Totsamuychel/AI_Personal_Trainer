from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from ai_trainer.db import crud, database
import re

router = Router()

class SettingsStates(StatesGroup):
    main_menu = State()
    setting_time = State()

from ai_trainer.bot.handlers.start import RegistrationStates
from aiogram.utils.keyboard import InlineKeyboardBuilder

@router.message(F.text == "/settings")
async def cmd_settings(message: types.Message):
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, str(message.from_user.id))
        if not user:
            await message.answer("Сначала зарегистрируйся с помощью /start")
            return
        
        status = "✅ Включены" if user.morning_tip_enabled else "❌ Выключены"
        time = user.morning_tip_time
        
        builder = InlineKeyboardBuilder()
        toggle_text = "Выключить советы" if user.morning_tip_enabled else "Включить советы"
        builder.button(text=toggle_text, callback_data="toggle_tips")
        builder.button(text="Изменить время", callback_data="change_time")
        builder.button(text="🔄 Перепройти регистрацию", callback_data="restart_registration")
        builder.adjust(1)
        
        text = (
            "⚙️ **Настройки**\n\n"
            f"Статус советов: {status}\n"
            f"Время советов: {time}\n\n"
            "Вы также можете обновить свои данные (имя, вес, цель), нажав кнопку ниже."
        )
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "restart_registration")
async def restart_registration(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский 🇷🇺", callback_data="lang_ru")
    builder.button(text="English 🇺🇸", callback_data="lang_en")
    builder.adjust(2)
    
    await callback.message.answer(
        "Начинаем процесс обновления данных.\nВыбери язык интерфейса / Choose your language:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.waiting_for_language)
    await callback.answer()

@router.callback_query(F.data == "toggle_tips")
async def toggle_tips(callback: types.CallbackQuery):
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, str(callback.from_user.id))
        new_status = 0 if user.morning_tip_enabled else 1
        await crud.update_user_scheduler_settings(db, user.id, new_status, user.morning_tip_time)
        
        status_text = "включены" if new_status else "выключены"
        await callback.answer(f"Утренние советы {status_text}!")
        
        # Refresh the message
        status = "✅ Включены" if new_status else "❌ Выключены"
        builder = InlineKeyboardBuilder()
        toggle_text = "Выключить советы" if new_status else "Включить советы"
        builder.button(text=toggle_text, callback_data="toggle_tips")
        builder.button(text="Изменить время", callback_data="change_time")
        builder.adjust(1)
        
        text = (
            "⚙️ **Настройки утренних советов**\n\n"
            f"Статус: {status}\n"
            f"Время: {user.morning_tip_time}\n\n"
            "Советы приходят каждое утро и содержат персонализированные рекомендации на основе твоего прогресса."
        )
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "change_time")
async def request_time(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи время в формате HH:MM (например, 07:30 или 09:00):")
    await state.set_state(SettingsStates.setting_time)
    await callback.answer()

@router.message(SettingsStates.setting_time)
async def process_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        await message.answer("Некорректный формат. Введи время в формате HH:MM (например, 08:30):")
        return
    
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, str(message.from_user.id))
        await crud.update_user_scheduler_settings(db, user.id, user.morning_tip_enabled, time_str)
        
        await message.answer(f"✅ Время получения советов изменено на {time_str}!")
        await state.clear()
