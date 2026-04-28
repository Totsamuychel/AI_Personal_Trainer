import pytest
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from ai_trainer.db.models import Base
from ai_trainer.db import database

# Use SQLite with aiosqlite for async testing
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_temp.db"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Save originals
    orig_get_engine = database.get_engine
    orig_get_session_factory = database.get_session_factory
    
    # Override database module functions
    database.get_engine = lambda: engine
    database.get_session_factory = lambda: async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    
    # Restore originals
    database.get_engine = orig_get_engine
    database.get_session_factory = orig_get_session_factory
    
    if os.path.exists("./test_temp.db"):
        try:
            os.remove("./test_temp.db")
        except PermissionError:
            pass

@pytest.fixture
async def db_session(engine):
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
        await session.rollback()
