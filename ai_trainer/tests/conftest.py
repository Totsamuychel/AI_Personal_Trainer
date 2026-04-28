import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ai_trainer.db.models import Base
from ai_trainer.db import database

# Use SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.db"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    # Save originals
    orig_get_engine = database.get_engine
    orig_get_session_factory = database.get_session_factory
    
    # Override database module functions to use this engine
    database.get_engine = lambda: engine
    database.get_session_factory = lambda: sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    
    # Restore originals
    database.get_engine = orig_get_engine
    database.get_session_factory = orig_get_session_factory
    
    # On Windows, deleting the file might fail even after dispose
    try:
        if os.path.exists("./test_temp.db"):
            os.remove("./test_temp.db")
    except PermissionError:
        pass

@pytest.fixture
def db_session(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
