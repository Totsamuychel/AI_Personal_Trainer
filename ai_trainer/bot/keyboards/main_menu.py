from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(language: str = "ru") -> ReplyKeyboardMarkup:
    """Returns the persistent main menu keyboard."""
    if language == "ru":
        buttons = [
            [KeyboardButton(text="🏋️ Тренировка"), KeyboardButton(text="🍎 Питание")],
            [KeyboardButton(text="📈 Прогресс"), KeyboardButton(text="📅 План на неделю")],
            [KeyboardButton(text="🧠 Задать вопрос ИИ"), KeyboardButton(text="⚙️ Настройки")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="🏋️ Workout"), KeyboardButton(text="🍎 Nutrition")],
            [KeyboardButton(text="📈 Progress"), KeyboardButton(text="📅 Weekly Plan")],
            [KeyboardButton(text="🧠 Ask AI"), KeyboardButton(text="⚙️ Settings")]
        ]
        
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..." if language == "ru" else "Choose an action..."
    )
