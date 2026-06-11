import pytest
from langchain_core.messages import AIMessage, HumanMessage

from ai_trainer.agent import trainer_agent
from ai_trainer.agent.tools.workout_tools import (
    log_workout_session_tool,
    get_workout_history_tool,
)
from ai_trainer.db import crud


# ─── _detect_topic (pure) ─────────────────────────────────────────────────────

def test_detect_topic_nutrition():
    assert trainer_agent._detect_topic("сколько белка и калорий в курице") == "nutrition"


def test_detect_topic_training():
    assert trainer_agent._detect_topic("how many sets for hypertrophy") == "training"


def test_detect_topic_none_when_no_keywords():
    assert trainer_agent._detect_topic("привет, как дела") is None


# ─── should_continue (pure) ───────────────────────────────────────────────────

def test_should_continue_routes_to_tools_when_tool_calls():
    msg = AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1"}])
    assert trainer_agent.should_continue({"messages": [msg]}) == "tools"


def test_should_continue_routes_to_store_memory_without_tool_calls():
    msg = AIMessage(content="just chatting")
    assert trainer_agent.should_continue({"messages": [msg]}) == "store_memory"


# ─── workout tools (DB-backed; Sheets disabled w/o spreadsheet id) ────────────

@pytest.mark.anyio
async def test_log_workout_tool_updates_personal_record(db_session):
    user = await crud.upsert_user(db_session, {"telegram_id": "70001", "name": "Liz"})

    result = await log_workout_session_tool.ainvoke({
        "telegram_id": "70001",
        "workout_type": "Push",
        "exercises": [{"name": "Bench Press", "sets": 3, "reps": [5, 5, 5], "weight_kg": [80, 80, 82.5]}],
        "duration_minutes": 60,
    })
    assert "successfully recorded" in result

    records = await crud.get_all_personal_records(db_session, user.id)
    assert len(records) == 1
    pr = records[0]
    assert pr.exercise == "Bench Press"
    assert pr.weight_kg == 82.5
    assert pr.reps == 5  # max reps performed at the max weight
    assert pr.one_rm_est == pytest.approx(crud.calculate_1rm(82.5, 5))


@pytest.mark.anyio
async def test_get_workout_history_tool_loads_exercises(db_session):
    """Regression: exercises must be eager-loaded, else async lazy-load raises MissingGreenlet."""
    user = await crud.upsert_user(db_session, {"telegram_id": "70002", "name": "Max"})
    await crud.create_workout_session(db_session, user.id,
        {"workout_type": "Pull", "duration_min": 45},
        [{"name": "Deadlift", "sets": 3, "reps": [5, 5, 5], "weight_kg": [120, 120, 120]}],
    )

    result = await get_workout_history_tool.ainvoke({"telegram_id": "70002"})
    assert "Pull" in result
    assert "Deadlift" in result  # would be missing if lazy-load failed


@pytest.mark.anyio
async def test_get_workout_history_tool_user_not_found():
    result = await get_workout_history_tool.ainvoke({"telegram_id": "no-such-user"})
    assert "not found" in result.lower()
