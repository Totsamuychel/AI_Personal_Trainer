"""
API endpoint tests using FastAPI TestClient + in-memory SQLite.
"""
import pytest
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from ai_trainer.db.models import Base
from ai_trainer.db import crud, database, models
from ai_trainer.api.app import app, get_db as app_get_db
from ai_trainer.api.routes.admin import get_db as admin_get_db
from ai_trainer.api import deps

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def api_client(test_engine):
    """HTTP client wired to the app with a test database and auth disabled."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_db():
        async with session_factory() as session:
            yield session

    async def override_auth():
        return None

    app.dependency_overrides[app_get_db] = override_db
    app.dependency_overrides[admin_get_db] = override_db
    app.dependency_overrides[deps.verify_admin_api_key] = override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def seeded_user(test_engine):
    """Creates a user and returns it for use in tests."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as db:
        user = await crud.upsert_user(db, {
            "telegram_id": "api_test_001",
            "name": "API Test User",
            "age": 28,
            "height_cm": 180.0,
            "weight_kg": 80.0,
            "goal": models.GoalType.hypertrophy,
            "level": "intermediate",
        })
        await crud.create_workout_session(db, user.id,
            {"workout_type": "Push", "duration_min": 60},
            [{"name": "Bench Press", "sets": 3, "reps": [8, 8, 7], "weight_kg": [75, 75, 75]}],
        )
        await crud.update_personal_record(db, user.id, "Bench Press", 75, 8)
    return user


# ─── Root ────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_root_returns_200(api_client):
    resp = await api_client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


# ─── Public user endpoints ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_existing_user(api_client, seeded_user):
    resp = await api_client.get(f"/api/users/{seeded_user.telegram_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "API Test User"
    assert data["goal"] in ("hypertrophy", "GoalType.hypertrophy", models.GoalType.hypertrophy.value)


@pytest.mark.anyio
async def test_get_nonexistent_user_returns_404(api_client):
    resp = await api_client.get("/api/users/0000000000")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_get_user_workouts(api_client, seeded_user):
    resp = await api_client.get(f"/api/users/{seeded_user.telegram_id}/workouts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_get_user_plan_not_found(api_client, seeded_user):
    # No plan was created for the seeded user
    resp = await api_client.get(f"/api/users/{seeded_user.telegram_id}/plan")
    assert resp.status_code == 404


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_admin_users_list(api_client, seeded_user):
    resp = await api_client.get("/admin/users")
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert any(u["telegram_id"] == seeded_user.telegram_id for u in users)


@pytest.mark.anyio
async def test_admin_user_records(api_client, seeded_user):
    resp = await api_client.get(f"/admin/users/{seeded_user.id}/records")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) >= 1
    assert records[0]["exercise"] == "Bench Press"
    assert records[0]["one_rm_est"] > 0


@pytest.mark.anyio
async def test_admin_user_workouts(api_client, seeded_user):
    resp = await api_client.get(f"/admin/users/{seeded_user.id}/workouts")
    assert resp.status_code == 200
    workouts = resp.json()
    assert len(workouts) >= 1
    assert workouts[0]["workout_type"] == "Push"
    assert len(workouts[0]["exercises"]) == 1


@pytest.mark.anyio
async def test_admin_user_stats(api_client, seeded_user):
    resp = await api_client.get(f"/admin/users/{seeded_user.id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "volume_history" in data
    assert len(data["volume_history"]) >= 1
    assert data["volume_history"][0]["total_volume"] > 0


@pytest.mark.anyio
async def test_admin_requires_key_when_configured(api_client):
    """When ADMIN_API_KEY env var is set, missing key → 401."""
    os.environ["ADMIN_API_KEY"] = "secret123"
    app.dependency_overrides.pop(deps.verify_admin_api_key, None)  # re-enable real auth
    try:
        resp = await api_client.get("/admin/users")
        assert resp.status_code == 401

        resp_ok = await api_client.get("/admin/users", headers={"X-Admin-API-Key": "secret123"})
        assert resp_ok.status_code == 200
    finally:
        del os.environ["ADMIN_API_KEY"]
        app.dependency_overrides[deps.verify_admin_api_key] = lambda: None
