"""
Seed script — adds a realistic test user to the real PostgreSQL database.
Run: python scripts/seed_test_db.py
Requires DATABASE_URL in .env or environment.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from ai_trainer.db import crud, database, models

TELEGRAM_ID = "999000001"

WORKOUTS = [
    # (days_ago, type, duration, exercises)
    (28, "Push", 55, [
        {"name": "Bench Press",    "sets": 4, "reps": [5,5,5,5],       "weight_kg": [80,80,80,80]},
        {"name": "Overhead Press", "sets": 3, "reps": [8,8,7],         "weight_kg": [50,50,50]},
        {"name": "Tricep Dips",    "sets": 3, "reps": [10,10,9],       "weight_kg": [0,0,0]},
    ]),
    (25, "Pull", 50, [
        {"name": "Deadlift",       "sets": 4, "reps": [5,5,5,4],       "weight_kg": [120,120,120,120]},
        {"name": "Pull-ups",       "sets": 4, "reps": [8,7,6,6],       "weight_kg": [0,0,0,0]},
        {"name": "Barbell Row",    "sets": 3, "reps": [8,8,8],         "weight_kg": [70,70,70]},
    ]),
    (22, "Legs", 60, [
        {"name": "Squat",          "sets": 5, "reps": [5,5,5,5,5],     "weight_kg": [100,100,100,100,100]},
        {"name": "Leg Press",      "sets": 3, "reps": [12,12,10],      "weight_kg": [160,160,160]},
        {"name": "Calf Raises",    "sets": 4, "reps": [15,15,15,15],   "weight_kg": [40,40,40,40]},
    ]),
    (18, "Push", 50, [
        {"name": "Bench Press",    "sets": 4, "reps": [5,5,5,5],       "weight_kg": [82.5,82.5,82.5,80]},
        {"name": "Incline DB Press","sets":3, "reps": [10,10,9],       "weight_kg": [30,30,30]},
        {"name": "Overhead Press", "sets": 3, "reps": [8,8,8],         "weight_kg": [52.5,52.5,52.5]},
    ]),
    (15, "Pull", 55, [
        {"name": "Deadlift",       "sets": 4, "reps": [5,5,5,5],       "weight_kg": [125,125,125,125]},
        {"name": "Pull-ups",       "sets": 4, "reps": [9,8,7,7],       "weight_kg": [0,0,0,0]},
        {"name": "Face Pulls",     "sets": 3, "reps": [15,15,15],      "weight_kg": [20,20,20]},
    ]),
    (12, "Legs", 65, [
        {"name": "Squat",          "sets": 5, "reps": [5,5,5,5,5],     "weight_kg": [102.5,102.5,102.5,102.5,102.5]},
        {"name": "Romanian DL",    "sets": 3, "reps": [10,10,10],      "weight_kg": [80,80,80]},
        {"name": "Leg Curl",       "sets": 3, "reps": [12,12,11],      "weight_kg": [35,35,35]},
    ]),
    (8,  "Push", 52, [
        {"name": "Bench Press",    "sets": 4, "reps": [5,5,5,5],       "weight_kg": [85,85,85,82.5]},
        {"name": "Overhead Press", "sets": 3, "reps": [8,8,7],         "weight_kg": [55,55,52.5]},
        {"name": "Cable Fly",      "sets": 3, "reps": [12,12,12],      "weight_kg": [15,15,15]},
    ]),
    (5,  "Pull", 58, [
        {"name": "Deadlift",       "sets": 4, "reps": [5,5,5,5],       "weight_kg": [127.5,127.5,127.5,125]},
        {"name": "Pull-ups",       "sets": 4, "reps": [10,9,8,7],      "weight_kg": [0,0,0,0]},
        {"name": "Barbell Row",    "sets": 3, "reps": [8,8,8],         "weight_kg": [75,75,75]},
    ]),
    (2,  "Legs", 60, [
        {"name": "Squat",          "sets": 5, "reps": [5,5,5,5,5],     "weight_kg": [105,105,105,105,102.5]},
        {"name": "Leg Press",      "sets": 3, "reps": [12,12,12],      "weight_kg": [170,170,170]},
        {"name": "Calf Raises",    "sets": 4, "reps": [15,15,15,15],   "weight_kg": [45,45,45,45]},
    ]),
    (0,  "Push", 50, [
        {"name": "Bench Press",    "sets": 4, "reps": [5,5,5,4],       "weight_kg": [87.5,87.5,87.5,87.5]},
        {"name": "Overhead Press", "sets": 4, "reps": [6,6,6,5],       "weight_kg": [57.5,57.5,57.5,57.5]},
        {"name": "Tricep Pushdown","sets": 3, "reps": [12,12,10],      "weight_kg": [25,25,25]},
    ]),
]

NUTRITION = [
    (2, "Завтрак",  "Овсянка с бананом, 2 яйца", 520,  35, 65, 12),
    (2, "Обед",     "Куриная грудка 200г, рис, огурец", 610, 52, 70, 8),
    (2, "Ужин",     "Лосось 150г, брокколи, картофель", 540, 38, 45, 18),
    (1, "Завтрак",  "Творог 200г с мёдом, кофе", 380,  32, 30, 9),
    (1, "Обед",     "Говядина 180г, гречка, салат", 680, 48, 55, 20),
    (1, "Перекус",  "Протеиновый коктейль, банан", 310,  28, 35, 4),
    (1, "Ужин",     "Треска 200г, овощи на гриле", 420,  42, 20, 12),
    (0, "Завтрак",  "Омлет 3 яйца с овощами", 380,  26, 8,  25),
    (0, "Обед",     "Куриный суп, хлеб ржаной", 490,  34, 52, 14),
    (0, "Ужин",     "Стейк 200г, картофельное пюре", 720, 50, 55, 28),
]

PLAN = {
    "week_type": "hypertrophy",
    "days": {
        "Monday":    {"type": "Push", "exercises": ["Bench Press", "Overhead Press", "Incline DB Press", "Tricep Dips"]},
        "Wednesday": {"type": "Pull", "exercises": ["Deadlift", "Pull-ups", "Barbell Row", "Face Pulls"]},
        "Friday":    {"type": "Legs", "exercises": ["Squat", "Leg Press", "Romanian DL", "Calf Raises"]},
    },
    "targets": {
        "Bench Press":    {"sets": 4, "reps": "8-10", "weight_pct_1rm": 0.72},
        "Squat":          {"sets": 4, "reps": "8-10", "weight_pct_1rm": 0.72},
        "Deadlift":       {"sets": 3, "reps": "6-8",  "weight_pct_1rm": 0.75},
        "Overhead Press": {"sets": 3, "reps": "8-12", "weight_pct_1rm": 0.70},
    }
}


async def seed():
    async with database.db_session() as db:
        # Remove existing test user if present
        existing = await crud.get_user_by_telegram_id(db, TELEGRAM_ID)
        if existing:
            await db.delete(existing)
            await db.commit()
            print(f"Removed existing test user (id={existing.id})")

        user = await crud.upsert_user(db, {
            "telegram_id": TELEGRAM_ID,
            "name":        "Алексей Тестов",
            "language":    "ru",
            "age":         27,
            "height_cm":   182.0,
            "weight_kg":   84.0,
            "goal":        models.GoalType.strength,
            "level":       "intermediate",
            "preferred_split": "PPL",
            "injuries":    [],
            "morning_tip_enabled": True,
            "morning_tip_time":    "08:00",
        })
        print(f"Created user: {user.name} (id={user.id}, telegram_id={user.telegram_id})")

        # Workouts
        for days_ago, wtype, duration, exercises in WORKOUTS:
            date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            session = await crud.create_workout_session(db, user.id, {
                "workout_type": wtype,
                "duration_min": duration,
                "date":         date,
                "notes":        f"Feeling: бодр. Pain: нет",
            }, exercises)

            for ex in exercises:
                best_1rm, best_w, best_r = 0, 0, 0
                for w, r in zip(ex["weight_kg"], ex["reps"]):
                    rm = crud.calculate_1rm(w, r)
                    if rm > best_1rm:
                        best_1rm, best_w, best_r = rm, w, r
                if best_1rm > 0:
                    await crud.update_personal_record(db, user.id, ex["name"], best_w, best_r)

        print(f"Created {len(WORKOUTS)} workout sessions")

        # Nutrition logs
        for days_ago, meal, desc, kcal, prot, carbs, fat in NUTRITION:
            date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            log = models.NutritionLog(
                user_id=user.id, date=date, meal_name=meal,
                description=desc, calories=kcal,
                protein_g=prot, carbs_g=carbs, fat_g=fat,
            )
            db.add(log)
        await db.commit()
        print(f"Created {len(NUTRITION)} nutrition logs")

        # Weekly plan
        plan = models.WeeklyPlan(
            user_id=user.id,
            week_number=1,
            week_type=models.WeekType.hypertrophy,
            start_date=datetime.now(timezone.utc),
            plan_data=PLAN,
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        print("Created weekly plan")

        prs = await crud.get_all_personal_records(db, user.id)
        print(f"\n=== Personal Records ({len(prs)}) ===")
        for pr in sorted(prs, key=lambda x: x.exercise):
            print(f"  {pr.exercise:<22} 1RM={pr.one_rm_est} кг  ({pr.weight_kg}×{pr.reps})")

    print("\nDone! Open admin panel → http://localhost:5173")


if __name__ == "__main__":
    asyncio.run(seed())
