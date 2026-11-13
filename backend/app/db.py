"""
Shared database engine and session provider.
Imported by API routers, services, and main.py alike.
Keeping it here breaks circular imports.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite
)


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for FastAPI dependencies or manual use."""
    with Session(engine) as session:
        yield session
