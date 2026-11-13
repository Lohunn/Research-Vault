"""Pytest configuration and shared fixtures for ResearchVault backend tests.

Sets up:
- In-memory SQLite database
- Test DB engine and session fixtures
- FastAPI dependency overrides
- TestClient for integration tests
- Mock vector store fixtures
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models.db import Collection, Document, Message


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create an isolated in-memory SQLite database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(name="db_session")
def db_session_fixture(test_engine) -> Generator[Session, None, None]:
    """Provide a database session attached to the test in-memory SQLite engine."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def patch_db_engine(test_engine, monkeypatch):
    """Automatically patch all module-level engine references to use test_engine."""
    monkeypatch.setattr("app.db.engine", test_engine)
    monkeypatch.setattr("app.api.collections.engine", test_engine, raising=False)
    monkeypatch.setattr("app.api.documents.engine", test_engine, raising=False)
    monkeypatch.setattr("app.api.chat.engine", test_engine, raising=False)
    monkeypatch.setattr("app.services.ingestion.engine", test_engine, raising=False)
    monkeypatch.setattr("app.services.answer.engine", test_engine, raising=False)


@pytest.fixture(name="client")
def client_fixture(db_session, test_engine) -> Generator[TestClient, None, None]:
    """Provide a TestClient with dependency overrides and clean database."""
    def _get_session_override() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_session_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(name="mock_vector_store")
def mock_vector_store_fixture():
    """Provide a mock VectorStore implementing upsert, search, and delete_by_doc_id."""
    store = MagicMock()
    store.upsert = AsyncMock(return_value=None)
    store.search = AsyncMock(return_value=[])
    store.delete_by_doc_id = AsyncMock(return_value=None)
    return store


@pytest.fixture(name="sample_collection")
def sample_collection_fixture(db_session: Session) -> Collection:
    """Create and return a sample Collection record in the test database."""
    col = Collection(
        id=uuid.uuid4(),
        name=f"test-col-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(col)
    db_session.commit()
    db_session.refresh(col)
    return col
