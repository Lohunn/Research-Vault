"""Tests for RetrievalService and AnswerService not-found path."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_chunk(score: float, idx: int = 0) -> dict:
    return {
        "score": score,
        "doc_id": f"doc-{idx}",
        "collection_id": "col-1",
        "filename": f"file{idx}.pdf",
        "page": idx + 1,
        "chunk_index": idx,
        "text": f"This is chunk number {idx} with enough text to test.",
    }


class MockVectorStore:
    """Fake VectorStore that returns pre-defined results."""

    def __init__(self, results: list[dict]) -> None:
        self._results = results

    async def search(
        self, query_vector: list[float], collection_id: str, top_k: int
    ) -> list[dict]:
        return self._results[:top_k]


# ---------------------------------------------------------------------------
# RetrievalService tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_returns_chunks_above_threshold():
    """With 2 high-score chunks the service should return both."""
    from app.services.retrieval import RetrievalService

    chunks = [_make_chunk(0.9, 0), _make_chunk(0.8, 1)]
    store = MockVectorStore(chunks)

    # Patch SentenceTransformer so we don't need model files on disk
    with patch.object(
        RetrievalService, "_get_embed_model"
    ) as mock_model_fn:
        mock_model = MagicMock()
        mock_encode_result = MagicMock()
        mock_encode_result.tolist.return_value = [0.1] * 384
        mock_model.encode.return_value = mock_encode_result
        mock_model_fn.return_value = mock_model

        with patch("app.services.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_TOP_K = 20
            mock_settings.ENABLE_HYBRID_SEARCH = False
            mock_settings.ENABLE_RERANKING = False
            mock_settings.SIMILARITY_THRESHOLD = 0.3

            svc = RetrievalService(store, "BAAI/bge-small-en-v1.5")
            results = await svc.retrieve("what is X?", "col-1")

    assert len(results) == 2
    assert results[0]["score"] == 0.9
    assert results[1]["score"] == 0.8


@pytest.mark.asyncio
async def test_retrieve_returns_empty_below_threshold():
    """When all chunk scores fall below threshold, retrieve() must return []."""
    from app.services.retrieval import RetrievalService

    chunks = [_make_chunk(0.1, 0), _make_chunk(0.05, 1)]
    store = MockVectorStore(chunks)

    with patch.object(
        RetrievalService, "_get_embed_model"
    ) as mock_model_fn:
        mock_model = MagicMock()
        mock_encode_result = MagicMock()
        mock_encode_result.tolist.return_value = [0.1] * 384
        mock_model.encode.return_value = mock_encode_result
        mock_model_fn.return_value = mock_model

        with patch("app.services.retrieval.settings") as mock_settings:
            mock_settings.RETRIEVAL_TOP_K = 20
            mock_settings.ENABLE_HYBRID_SEARCH = False
            mock_settings.ENABLE_RERANKING = False
            mock_settings.SIMILARITY_THRESHOLD = 0.3

            svc = RetrievalService(store, "BAAI/bge-small-en-v1.5")
            results = await svc.retrieve("what is X?", "col-1")

    assert results == []


# ---------------------------------------------------------------------------
# AnswerService tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_answer_not_found_path():
    """When retrieval returns no chunks the SSE stream must yield the not-found message."""
    from app.services.answer import AnswerService, _NOT_FOUND_MSG

    # Mock LLMProvider (not called in not-found path)
    mock_llm = MagicMock()

    # Mock RetrievalService that always returns empty
    mock_retrieval = MagicMock()
    mock_retrieval.retrieve = AsyncMock(return_value=[])

    svc = AnswerService(llm=mock_llm, retrieval=mock_retrieval)

    # Patch _save_message so we don't need a real DB
    with patch.object(svc, "_save_message", new=AsyncMock()):
        events: list[dict] = []
        async for sse_line in svc.stream_answer("unknowable question", "col-1", []):
            # each line is "data: {...}\n\n"
            if sse_line.startswith("data: "):
                payload = json.loads(sse_line[len("data: "):].strip())
                events.append(payload)

    assert len(events) == 3
    assert events[0] == {"type": "token", "content": _NOT_FOUND_MSG}
    assert events[1] == {"type": "citations", "citations": []}
    assert events[2] == {"type": "done"}
