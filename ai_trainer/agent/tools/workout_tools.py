from langchain.tools import tool
from ai_trainer.db import crud, database
from ai_trainer.sheets.client import SheetsClient
from loguru import logger

sheets = SheetsClient()

@tool
async def log_workout_session_tool(
    telegram_id: str,
    workout_type: str,
    exercises: list[dict],
    duration_minutes: int,
    notes: str = ""
) -> str:
    """
    Records a workout in the database and Google Sheets.
    exercises should be a list of dicts: [{"name": "Bench Press", "sets": 4, "reps": [5,5,5,4], "weight_kg": [80,80,80,80]}]
    """
    try:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            if not user:
                return "Error: user not found."
            
            workout_data = {
                "workout_type": workout_type,
                "duration_min": duration_minutes,
                "notes": notes
            }
            
            await crud.create_workout_session(db, user.id, workout_data, exercises)
            
            # Update records
            for ex in exercises:
                weights = ex.get('weight_kg', [])
                reps_list = ex.get('reps', [])
                
                if not weights or not reps_list:
                    continue
                    
                max_weight = max(weights)
                
                # Find the maximum reps performed with the maximum weight
                max_reps_with_max_weight = 0
                for w, r in zip(weights, reps_list):
                    if w == max_weight:
                        if r > max_reps_with_max_weight:
                            max_reps_with_max_weight = r
                
                if max_weight > 0 and max_reps_with_max_weight > 0:
                    await crud.update_personal_record(db, user.id, ex['name'], max_weight, max_reps_with_max_weight)
            
            # Sync to Sheets
            await sheets.log_workout(user.name, {
                "workout_type": workout_type,
                "exercises": exercises
            })
            
        return f"✅ Workout '{workout_type}' successfully recorded! {len(exercises)} exercises completed."
    except Exception as e:
        logger.error(f"Error in log_workout_session_tool: {e}")
        return f"❌ Error recording workout: {str(e)}"

@tool
async def get_workout_history_tool(telegram_id: str, last_n: int = 5) -> str:
    """Returns the user's recent workout history."""
    try:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            if not user:
                return "User not found."
            
            history = await crud.get_workout_history(db, user.id, last_n)
            if not history:
                return "Workout history is empty."
            
            res = "Recent workouts:\n"
            for s in history:
                res += f"- {s.date.strftime('%Y-%m-%d')}: {s.workout_type} ({s.duration_min} min)\n"
                for ex in s.exercises:
                    res += f"  • {ex.name}: {ex.sets} sets, weight {ex.weight_kg} kg\n"
            return res
    except Exception as e:
        logger.error(f"Error in get_workout_history_tool: {e}")
        return f"❌ Error retrieving history: {str(e)}"
