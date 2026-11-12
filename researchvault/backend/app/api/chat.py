"""Chat API – SSE streaming endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.config import settings
from app.db import engine
from app.models.db import Collection
from app.models.schemas import ChatRequest
from app.services.answer import AnswerService
from app.services.llm import LLMProvider
from app.services.retrieval import RetrievalService
from app.stores.vector_store import get_vector_store

router = APIRouter(tags=["chat"])


@router.post("/collections/{collection_id}/chat")
async def chat(
    collection_id: uuid.UUID,
    body: ChatRequest,
) -> StreamingResponse:
    """Stream an SSE response for a chat question against a document collection."""
    with Session(engine) as session:
        col = session.get(Collection, collection_id)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
    answer_service = AnswerService(
        llm=LLMProvider(),
        retrieval=RetrievalService(
            vector_store=get_vector_store(),
            embed_model_name=settings.EMBEDDING_MODEL,
        ),
    )
    return StreamingResponse(
        answer_service.stream_answer(
            question=body.question,
            collection_id=str(collection_id),
            history=body.history,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
