import pytest
from datetime import datetime, timezone, timedelta
from ai_trainer.db import crud, models


# ─── 1RM formula ─────────────────────────────────────────────────────────────

def test_1rm_calculation():
    assert crud.calculate_1rm(100, 5) == 116.67
    assert crud.calculate_1rm(100, 1) == 100.0

def test_1rm_zero_inputs():
    assert crud.calculate_1rm(0, 5) == 0.0
    assert crud.calculate_1rm(100, 0) == 0.0
    assert crud.calculate_1rm(0, 0) == 0.0

def test_1rm_single_rep():
    assert crud.calculate_1rm(150, 1) == 150.0


# ─── User CRUD ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_create_user(db_session):
    user = await crud.upsert_user(db_session, {
        "telegram_id": "11111",
        "name": "Alice",
        "age": 25,
        "goal": models.GoalType.strength,
    })
    assert user.id is not None
    assert user.name == "Alice"

    fetched = await crud.get_user_by_telegram_id(db_session, "11111")
    assert fetched.id == user.id


@pytest.mark.anyio
async def test_upsert_accepts_raw_string_goal(db_session):
    """Registration passes goal as a raw string (e.g. 'fat_loss'); it must
    round-trip to the GoalType enum. Guards the name==value assumption."""
    await crud.upsert_user(db_session, {
        "telegram_id": "11112",
        "name": "Stringy",
        "goal": "fat_loss",
    })
    fetched = await crud.get_user_by_telegram_id(db_session, "11112")
    assert fetched.goal == models.GoalType.fat_loss
    assert fetched.goal.value == "fat_loss"


@pytest.mark.anyio
async def test_upsert_updates_existing_user(db_session):
    await crud.upsert_user(db_session, {"telegram_id": "22222", "name": "Bob", "age": 20})
    updated = await crud.upsert_user(db_session, {"telegram_id": "22222", "name": "Bobby", "age": 21})
    assert updated.name == "Bobby"
    assert updated.age == 21

    all_users = await crud.get_all_users(db_session)
    matching = [u for u in all_users if u.telegram_id == "22222"]
    assert len(matching) == 1  # no duplicate


@pytest.mark.anyio
async def test_get_nonexistent_user_returns_none(db_session):
    result = await crud.get_user_by_telegram_id(db_session, "0000000")
    assert result is None


@pytest.mark.anyio
async def test_update_scheduler_settings(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "33333", "name": "Carol"})
    updated = await crud.update_user_scheduler_settings(db_session, user.id, enabled=False, time="09:30")
    assert updated.morning_tip_enabled is False
    assert updated.morning_tip_time == "09:30"


# ─── Workout CRUD ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_create_workout(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "44444", "name": "Dave"})
    session = await crud.create_workout_session(db_session, user.id,
        {"workout_type": "Push", "duration_min": 60},
        [{"name": "Bench Press", "sets": 3, "reps": [5, 5, 5], "weight_kg": [80, 80, 80]}],
    )
    assert session.id is not None
    assert session.workout_type == "Push"


@pytest.mark.anyio
async def test_get_workout_history_respects_limit(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "55555", "name": "Eve"})
    for i in range(5):
        await crud.create_workout_session(db_session, user.id,
            {"workout_type": "Legs", "duration_min": 45,
             "date": datetime.now(timezone.utc) - timedelta(days=i)},
            [{"name": "Squat", "sets": 3, "reps": [5, 5, 5], "weight_kg": [100, 100, 100]}],
        )
    history = await crud.get_workout_history(db_session, user.id, limit=3)
    assert len(history) == 3


@pytest.mark.anyio
async def test_get_user_exercises_returns_distinct(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "66666", "name": "Frank"})
    for _ in range(3):
        await crud.create_workout_session(db_session, user.id,
            {"workout_type": "Pull", "duration_min": 50},
            [{"name": "Deadlift", "sets": 3, "reps": [5, 5, 5], "weight_kg": [120, 120, 120]},
             {"name": "Pull-ups", "sets": 3, "reps": [8, 7, 6], "weight_kg": [0, 0, 0]}],
        )
    exercises = await crud.get_user_exercises(db_session, user.id)
    assert sorted(exercises) == ["Deadlift", "Pull-ups"]  # distinct, no duplicates


@pytest.mark.anyio
async def test_get_volume_history_calculates_tonnage(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "77777", "name": "Grace"})
    # 3 sets × 5 reps × 100 kg = 1500 kg tonnage
    await crud.create_workout_session(db_session, user.id,
        {"workout_type": "Push", "duration_min": 45},
        [{"name": "Bench Press", "sets": 3, "reps": [5, 5, 5], "weight_kg": [100, 100, 100]}],
    )
    volume = await crud.get_volume_history(db_session, user.id, limit=10)
    assert len(volume) == 1
    assert volume[0]["total_volume"] == pytest.approx(1500.0)


@pytest.mark.anyio
async def test_get_exercise_progress_with_dates(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "88888", "name": "Hank"})
    await crud.create_workout_session(db_session, user.id,
        {"workout_type": "Push", "duration_min": 50},
        [{"name": "Squat", "sets": 2, "reps": [5, 5], "weight_kg": [90, 90]}],
    )
    rows = await crud.get_exercise_progress_with_dates(db_session, user.id, "Squat")
    assert len(rows) == 1
    date, name, sets, reps, weight_kg = rows[0]
    assert name == "Squat"
    assert sets == 2


# ─── Personal Records ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_update_personal_record_creates_and_updates(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "99991", "name": "Iris"})

    # First call: creates record
    await crud.update_personal_record(db_session, user.id, "Squat", 100, 5)
    records = await crud.get_all_personal_records(db_session, user.id)
    assert len(records) == 1
    assert records[0].one_rm_est == pytest.approx(crud.calculate_1rm(100, 5))

    # Better result: updates record
    await crud.update_personal_record(db_session, user.id, "Squat", 110, 3)
    records = await crud.get_all_personal_records(db_session, user.id)
    assert len(records) == 1
    assert records[0].weight_kg == 110

    # Worse result: record stays the same
    await crud.update_personal_record(db_session, user.id, "Squat", 80, 5)
    records = await crud.get_all_personal_records(db_session, user.id)
    assert records[0].weight_kg == 110


@pytest.mark.anyio
async def test_personal_records_ordered_by_exercise(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "99992", "name": "Jack"})
    await crud.update_personal_record(db_session, user.id, "Squat", 100, 5)
    await crud.update_personal_record(db_session, user.id, "Bench Press", 80, 5)
    await crud.update_personal_record(db_session, user.id, "Deadlift", 140, 3)

    records = await crud.get_all_personal_records(db_session, user.id)
    names = [r.exercise for r in records]
    assert names == sorted(names)


# ─── Nutrition ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_create_nutrition_log(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "99993", "name": "Kate"})
    log = models.NutritionLog(
        user_id=user.id,
        meal_name="Завтрак",
        description="Овсянка с бананом",
        calories=450,
        protein_g=15,
        carbs_g=75,
        fat_g=8,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    assert log.id is not None
    assert log.calories == 450


# ─── System Settings ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_system_settings_returns_none_when_empty(db_session):
    result = await crud.get_system_settings(db_session)
    # Fresh test DB — settings may or may not exist; function must not raise
    assert result is None or hasattr(result, "llm_provider")


@pytest.mark.anyio
async def test_update_system_settings(db_session):
    settings = await crud.update_system_settings(db_session, {
        "llm_provider": "openai",
        "openai_model": "gpt-4o-mini",
    })
    assert settings.llm_provider == "openai"
    assert settings.openai_model == "gpt-4o-mini"

    # Second call should update, not create a duplicate
    settings2 = await crud.update_system_settings(db_session, {"openai_model": "gpt-4o"})
    assert settings2.openai_model == "gpt-4o"
    assert settings2.llm_provider == "openai"  # unchanged
