import pytest
from ai_trainer.db import crud, models

def test_create_user(db_session):
    user_data = {
        "telegram_id": "12345",
        "name": "Test User",
        "age": 25,
        "goal": models.GoalType.strength
    }
    user = crud.create_user(db_session, user_data)
    assert user.id is not None
    assert user.name == "Test User"
    
    db_user = crud.get_user_by_telegram_id(db_session, "12345")
    assert db_user.id == user.id

def test_create_workout(db_session):
    # Setup user
    user = crud.create_user(db_session, {"telegram_id": "67890", "name": "Athlete"})
    
    workout_data = {
        "workout_type": "Push",
        "duration_min": 60
    }
    exercises = [
        {
            "name": "Bench Press",
            "sets": 3,
            "reps": [5, 5, 5],
            "weight_kg": [80, 80, 80]
        }
    ]
    
    session = crud.create_workout_session(db_session, user.id, workout_data, exercises)
    assert session.id is not None
    assert len(session.exercises) == 1
    assert session.exercises[0].name == "Bench Press"

def test_1rm_calculation():
    # 100kg for 5 reps: 100 * (1 + 5/30) = 116.66
    rm = crud.calculate_1rm(100, 5)
    assert rm == 116.67
    
    # 100kg for 1 rep: should be 100
    rm_one = crud.calculate_1rm(100, 1)
    assert rm_one == 100.0
