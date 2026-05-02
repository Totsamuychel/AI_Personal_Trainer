from langchain.tools import tool
from datetime import datetime, timedelta, timezone
from ai_trainer.db import crud, database, models
from ai_trainer.sheets.client import SheetsClient
from sqlalchemy import select, update as sa_update
from loguru import logger
import json

sheets = SheetsClient()

PERIODIZATION_CYCLE = [
    {
        "week_type": "strength",
        "name": "💪 Strength Week",
        "intensity": "85-90% of 1RM",
        "intensity_val": 0.875,
        "sets": 4,
        "reps_range": "4-6",
        "rest_sec": 180,
    },
    {
        "week_type": "hypertrophy",
        "name": "🏗️ Hypertrophy",
        "intensity": "70-75% of 1RM",
        "intensity_val": 0.725,
        "sets": 4,
        "reps_range": "8-12",
        "rest_sec": 90,
    },
    {
        "week_type": "volume",
        "name": "📦 Volume Week",
        "intensity": "60-65% of 1RM",
        "intensity_val": 0.625,
        "sets": 3,
        "reps_range": "12-15",
        "rest_sec": 60,
    },
    {
        "week_type": "deload",
        "name": "🔄 Deload Week",
        "intensity": "50% of 1RM",
        "intensity_val": 0.50,
        "sets": 2,
        "reps_range": "10-12",
        "rest_sec": 60,
    },
]

@tool
async def generate_weekly_plan_tool(telegram_id: str, split_type: str = "PPL") -> str:
    """
    Generates a highly detailed workout plan for the next week.
    split_type can be 'Full Body', 'PPL' (Push/Pull/Legs), or 'Upper-Lower'.
    Includes specific exercises, sets, reps, and target weights based on user PRs.
    """
    try:
        logger.info(f"Generating detailed {split_type} plan for {telegram_id}")
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, str(telegram_id))
            if not user: return "Error: User not found."

            # Update user preference if provided
            if split_type:
                user.preferred_split = split_type
                await db.commit()

            result = await db.execute(
                select(models.WeeklyPlan).filter(models.WeeklyPlan.user_id == user.id).order_by(models.WeeklyPlan.week_number.desc())
            )
            last_plan = result.scalars().first()
            next_week_num = (last_plan.week_number + 1) if last_plan else 1
            week_info = PERIODIZATION_CYCLE[(next_week_num - 1) % 4]
            
            pr_result = await db.execute(select(models.PersonalRecord).filter(models.PersonalRecord.user_id == user.id))
            pr_map = {pr.exercise.lower(): pr.one_rm_est for pr in pr_result.scalars().all()}
            
            days = []
            if split_type.lower() == "full body":
                days = [
                    {"day": "Monday", "type": "Full Body A", "exercises": [
                        {"name": "Squat", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Bench Press", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Pull-ups", "sets": 3, "reps": "Max"}
                    ]},
                    {"day": "Wednesday", "type": "Full Body B", "exercises": [
                        {"name": "Deadlift", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Overhead Press", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Rows", "sets": week_info["sets"], "reps": week_info["reps_range"]}
                    ]},
                    {"day": "Friday", "type": "Full Body A", "exercises": [
                        {"name": "Squat", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Incline Press", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Bicep Curls", "sets": 3, "reps": "12-15"}
                    ]}
                ]
            else: # Default to PPL
                days = [
                    {"day": "Monday", "type": "Push", "exercises": [
                        {"name": "Bench Press", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Overhead Press", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Triceps Extensions", "sets": 3, "reps": "12-15"}
                    ]},
                    {"day": "Wednesday", "type": "Pull", "exercises": [
                        {"name": "Deadlift", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Rows", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Bicep Curls", "sets": 3, "reps": "12-15"}
                    ]},
                    {"day": "Friday", "type": "Legs", "exercises": [
                        {"name": "Squat", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Leg Press", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                        {"name": "Calf Raises", "sets": 4, "reps": "15-20"}
                    ]}
                ]

            for d in days:
                for ex in d["exercises"]:
                    one_rm = pr_map.get(ex["name"].lower())
                    ex["target_weight"] = round((one_rm * week_info["intensity_val"]) / 2.5) * 2.5 if one_rm else "TBD"

            plan_data = {"week_number": next_week_num, "week_type": week_info["week_type"], "week_name": week_info["name"], "days": days}
            
            now = datetime.now(timezone.utc)
            new_plan = models.WeeklyPlan(user_id=user.id, week_number=next_week_num, week_type=week_info["week_type"], 
                                         start_date=now + timedelta(days=(7-now.weekday())), plan_data=plan_data, is_active=1)
            db.add(new_plan)
            await db.execute(sa_update(models.WeeklyPlan).filter(models.WeeklyPlan.user_id == user.id, models.WeeklyPlan.id != new_plan.id).values(is_active=0))
            await db.commit()
            
            # Sync and get detailed report
            await sheets.update_weekly_plan(plan_data)
            
            report = f"✅ Составлен детальный план '{split_type}' на неделю #{next_week_num} ({week_info['name']}).\n"
            report += f"📊 Интенсивность: {week_info['intensity']}. Данные синхронизированы с Google Таблицей."
            return report
            
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        return f"❌ Ошибка при создании плана: {str(e)}"

@tool
async def update_sheet_workout_report_tool(telegram_id: str, exercise_name: str, weight: float, reps: int) -> str:
    """
    Updates the Google Sheet directly with a specific exercise result performed by the user.
    Use this when the user reports a finished exercise in chat.
    """
    try:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, str(telegram_id))
            if not user: return "Error: User not found."
            
            # 1. Update DB Personal Record if applicable
            await crud.update_personal_record(db, user.id, exercise_name, weight, reps)
            
            # 2. Add to Google Sheets "Workout Results" tab
            await sheets.log_workout(user.name, {
                "workout_type": "Chat Update",
                "exercises": [{"name": exercise_name, "sets": 1, "reps": [reps], "weight_kg": [weight]}]
            })
            
            return f"✅ Записал в таблицу: {exercise_name} — {weight}кг на {reps} повт. Твой прогресс обновлен!"
    except Exception as e:
        return f"❌ Не удалось обновить таблицу: {e}"

@tool
async def get_current_plan_tool(telegram_id: str) -> str:
    """Returns the current active workout plan for the user."""
    try:
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            if not user:
                return "User not found."
            
            result = await db.execute(
                select(models.WeeklyPlan).filter(
                    models.WeeklyPlan.user_id == user.id, 
                    models.WeeklyPlan.is_active == 1
                )
            )
            plan = result.scalars().first()
            
            if not plan:
                return "You don't have an active plan yet. Use /plan to generate one."
            
            pd = plan.plan_data
            res = f"📅 Plan for week #{pd['week_number']} ({pd['week_name']}):\n\n"
            for day in pd['days']:
                res += f"🔹 {day['day']} ({day['type']}):\n"
                for ex in day['exercises']:
                    res += f"  • {ex['name']}: {ex['sets']}x{ex['reps']} @ {ex['target_weight']} kg\n"
                res += "\n"
            return res
    except Exception as e:
        logger.error(f"Error in get_current_plan_tool: {e}")
        return f"❌ Error retrieving plan: {str(e)}"
