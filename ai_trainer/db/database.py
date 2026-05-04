import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv
from typing import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

load_dotenv()

# For asyncpg, the URL should be postgresql+asyncpg://...
DATABASE_URL = os.getenv("DATABASE_URL")
SYNC_DATABASE_URL = DATABASE_URL
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Engine will be initialized on first request if needed
_engine = None
_sync_engine = None

def get_engine():
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        kwargs = {"echo": False}
        if DATABASE_URL.startswith("postgresql"):
            kwargs.update({
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 1800
            })
            
        _engine = create_async_engine(DATABASE_URL, **kwargs)
    return _engine

def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Convert async URL to sync if necessary
        if url.startswith("sqlite+aiosqlite://"):
            url = url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        elif url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            
        kwargs = {"echo": False}
        if url.startswith("postgresql"):
            kwargs.update({
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 1800
            })
            
        _sync_engine = create_engine(url, **kwargs)
    return _sync_engine

def get_session_factory():
    engine = get_engine()
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

def get_sync_session_factory():
    engine = get_sync_engine()
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions."""
    async_session = get_session_factory()
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@contextmanager
def sync_db_session() -> Generator[Session, None, None]:
    """Sync context manager for database sessions."""
    session_factory = get_sync_session_factory()
    with session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
