# File: tests/conftest.py
"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine per test — full isolation."""
    # StaticPool + check_same_thread=False lets the TestClient's worker
    # threads share the single in-memory connection (needed for SSE streams).
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine):
    """Provide a DB session. Tables are fresh per test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with DB dependency overridden."""
    from fastapi.testclient import TestClient

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
