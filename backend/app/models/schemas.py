from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class CollectionCreate(BaseModel):
    name: str


class CollectionRead(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: uuid.UUID
    collection_id: uuid.UUID
    filename: str
    title: str | None
    num_pages: int
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class CitationSchema(BaseModel):
    index: int
    doc_id: str
    filename: str
    page: int
    snippet: str


class MessageRead(BaseModel):
    id: uuid.UUID
    collection_id: uuid.UUID
    role: str
    content: str
    citations: list[CitationSchema]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("citations", mode="before")
    @classmethod
    def parse_citations(cls, v: Any) -> list[Any]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []


class ChatRequest(BaseModel):
    question: str
    history: list[dict[str, Any]] = []
