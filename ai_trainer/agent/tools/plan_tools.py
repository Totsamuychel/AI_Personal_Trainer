from langchain.tools import tool
from datetime import datetime, timedelta
from ai_trainer.db import crud, database, models
from sqlalchemy import select, update as sa_update
from loguru import logger
import json

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
def generate_weekly_plan_tool(telegram_id: str) -> str:
    """
    Generates a workout plan for the next week for the user.
    Automatically determines the week type from the cycle (strength/hypertrophy/volume/deload).
    """
    try:
        with database.sync_db_session() as db:
            user = crud.get_user_by_telegram_id_sync(db, telegram_id)
            if not user:
                return "Error: User not found."

            # Determine the next week number
            last_plan = db.query(models.WeeklyPlan).filter(
                models.WeeklyPlan.user_id == user.id
            ).order_by(models.WeeklyPlan.week_number.desc()).first()
            
            next_week_num = (last_plan.week_number + 1) if last_plan else 1
            week_info = PERIODIZATION_CYCLE[(next_week_num - 1) % 4]
            
            # Get records to calculate weights
            prs = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == user.id).all()
            pr_map = {pr.exercise.lower(): pr.one_rm_est for pr in prs}
            
            # Basic plan structure
            plan_data = {
                "week_number": next_week_num,
                "week_type": week_info["week_type"],
                "week_name": week_info["name"],
                "days": [
                    {
                        "day": "Monday",
                        "type": "Push",
                        "exercises": [
                            {"name": "Bench Press", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                            {"name": "Overhead Press", "sets": week_info["sets"], "reps": week_info["reps_range"]}
                        ]
                    },
                    {
                        "day": "Wednesday",
                        "type": "Pull",
                        "exercises": [
                            {"name": "Pull-ups", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                            {"name": "Bent-over Row", "sets": week_info["sets"], "reps": week_info["reps_range"]}
                        ]
                    },
                    {
                        "day": "Friday",
                        "type": "Legs",
                        "exercises": [
                            {"name": "Squat", "sets": week_info["sets"], "reps": week_info["reps_range"]},
                            {"name": "Deadlift", "sets": week_info["sets"], "reps": week_info["reps_range"]}
                        ]
                    }
                ]
            }
            
            # Calculate target weights
            for day in plan_data["days"]:
                for ex in day["exercises"]:
                    one_rm = pr_map.get(ex["name"].lower())
                    if one_rm:
                        target_weight = round((one_rm * week_info["intensity_val"]) / 2.5) * 2.5
                        ex["target_weight"] = target_weight
                    else:
                        ex["target_weight"] = "To be determined"

            # Save the plan to the DB
            new_plan = models.WeeklyPlan(
                user_id=user.id,
                week_number=next_week_num,
                week_type=week_info["week_type"],
                start_date=datetime.now() + timedelta(days=(7 - datetime.now().weekday())),
                plan_data=plan_data,
                is_active=1
            )
            db.add(new_plan)
            # Ensure the new_plan is flushed so its ID is available for the filter
            db.flush()
            
            # Deactivate old plans
            db.query(models.WeeklyPlan).filter(
                models.WeeklyPlan.user_id == user.id, 
                models.WeeklyPlan.id != new_plan.id
            ).update({"is_active": 0})
            
            return f"✅ Plan generated for week #{next_week_num} ({week_info['name']})."
            
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        return f"❌ Error generating plan: {str(e)}"

@tool
def get_current_plan_tool(telegram_id: str) -> str:
    """Returns the current active workout plan for the user."""
    with database.sync_db_session() as db:
        user = crud.get_user_by_telegram_id_sync(db, telegram_id)
        if not user:
            return "User not found."
        
        plan = db.query(models.WeeklyPlan).filter(
            models.WeeklyPlan.user_id == user.id, 
            models.WeeklyPlan.is_active == 1
        ).first()
        
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
