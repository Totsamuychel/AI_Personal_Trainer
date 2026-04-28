from langchain.tools import tool
from ai_trainer.db import crud, database
from sqlalchemy.orm import Session

@tool
def log_workout_session_tool(
    telegram_id: str,
    workout_type: str,
    exercises: list[dict],
    duration_minutes: int,
    notes: str = ""
) -> str:
    """
    Записывает тренировку в базу данных.
    exercises должен быть списком словарей: [{"name": "Жим лёжа", "sets": 4, "reps": [5,5,5,4], "weight_kg": [80,80,80,80]}]
    """
    db = next(database.get_db())
    user = crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        return "Ошибка: пользователь не найден."
    
    workout_data = {
        "workout_type": workout_type,
        "duration_min": duration_minutes,
        "notes": notes
    }
    
    try:
        session = crud.create_workout_session(db, user.id, workout_data, exercises)
        
        # Обновляем рекорды
        for ex in exercises:
            max_weight = max(ex.get('weight_kg', [0]))
            # Берем минимальное кол-во повторов с этим весом для консервативной оценки 1RM
            reps = ex.get('reps', [0])[0] 
            crud.update_personal_record(db, user.id, ex['name'], max_weight, reps)
            
        return f"✅ Тренировка '{workout_type}' успешно записана! Выполнено {len(exercises)} упражнений."
    except Exception as e:
        return f"❌ Ошибка при записи тренировки: {str(e)}"

@tool
def get_workout_history_tool(telegram_id: str, last_n: int = 5) -> str:
    """Возвращает историю последних тренировок пользователя."""
    db = next(database.get_db())
    user = crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        return "Пользователь не найден."
    
    history = crud.get_workout_history(db, user.id, last_n)
    if not history:
        return "История тренировок пуста."
    
    res = "Последние тренировки:\n"
    for s in history:
        res += f"- {s.date.strftime('%Y-%m-%d')}: {s.workout_type} ({s.duration_min} мин)\n"
        for ex in s.exercises:
            res += f"  • {ex.name}: {ex.sets} подходов, вес {ex.weight_kg} кг\n"
    return res
