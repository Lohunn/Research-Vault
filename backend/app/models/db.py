from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Collection(SQLModel, table=True):
    __tablename__ = "collection"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    name: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class Document(SQLModel, table=True):
    __tablename__ = "document"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    collection_id: uuid.UUID = Field(foreign_key="collection.id", index=True)
    filename: str
    stored_filename: str
    title: Optional[str] = None
    num_pages: int = 0
    status: str = "processing"
    error_msg: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=_utcnow)


class Message(SQLModel, table=True):
    __tablename__ = "message"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    collection_id: uuid.UUID = Field(foreign_key="collection.id", index=True)
    role: str
    content: str
    citations: str = "[]"
    created_at: datetime = Field(default_factory=_utcnow)
