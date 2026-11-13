"""RetrievalService: embed → vector search → optional hybrid BM25 → optional reranking."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.stores.vector_store import VectorStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton for cross-encoder (avoid loading at import time)
# ---------------------------------------------------------------------------

_cross_encoder: "object | None" = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder  # type: ignore

        _cross_encoder = CrossEncoder("BAAI/bge-reranker-base")
    return _cross_encoder


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion helper
# ---------------------------------------------------------------------------


def _rrf_merge(
    ranked_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """Merge multiple ranked result lists via Reciprocal Rank Fusion.

    Each item is identified by ``(doc_id, chunk_index)``.
    """
    scores: dict[tuple, float] = {}
    items: dict[tuple, dict] = {}

    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            key = (str(item.get("doc_id", "")), int(item.get("chunk_index", 0)))
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            items[key] = item

    merged = sorted(items.keys(), key=lambda key: scores[key], reverse=True)
    result = []
    for key in merged:
        item = dict(items[key])
        item["score"] = scores[key]
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# RetrievalService
# ---------------------------------------------------------------------------


class RetrievalService:
    """Retrieve relevant chunks for a question from a named collection."""

    def __init__(self, vector_store: "VectorStore", embed_model_name: str) -> None:
        self.vector_store = vector_store
        self.embed_model_name = embed_model_name
        self._embed_model = None  # lazy

    # ------------------------------------------------------------------
    # Embedding (cached model, lazy-loaded)
    # ------------------------------------------------------------------

    def _get_embed_model(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._embed_model = SentenceTransformer(self.embed_model_name)
        return self._embed_model

    def _embed(self, text: str) -> list[float]:
        model = self._get_embed_model()
        return model.encode(text, normalize_embeddings=True).tolist()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        question: str,
        collection_id: str,
        rewritten_question: str | None = None,
    ) -> list[dict]:
        """Return top-k relevant chunks for *question* from *collection_id*.

        Steps:
        1. Embed the (rewritten) question.
        2. Vector-store ANN search → top-k candidates.
        3. Optionally fuse with BM25 using Reciprocal Rank Fusion.
        4. Optionally rerank with a cross-encoder.
        5. If best score < threshold → return [].
        6. Return up to RERANK_TOP_K (or RETRIEVAL_TOP_K) chunks.
        """
        query_text = rewritten_question or question

        # 1. Embed question (sync model run in executor)
        loop = asyncio.get_event_loop()
        query_vector = await loop.run_in_executor(None, self._embed, query_text)

        # 2. Vector search
        raw_results: list[dict] = await self.vector_store.search(
            collection_id=collection_id,
            query_vector=query_vector,
            top_k=settings.RETRIEVAL_TOP_K,
        )

        if not raw_results:
            return []

        # 3. Optional BM25 hybrid search + RRF merge
        if settings.ENABLE_HYBRID_SEARCH:
            raw_results = await loop.run_in_executor(
                None,
                self._hybrid_rrf,
                raw_results,
                query_text,
            )

        # 4. Optional cross-encoder reranking
        if settings.ENABLE_RERANKING:
            raw_results = await loop.run_in_executor(
                None,
                self._rerank,
                raw_results,
                query_text,
            )
            raw_results = raw_results[: settings.RERANK_TOP_K]

        # 5. Similarity threshold gate
        if not raw_results or raw_results[0]["score"] < settings.SIMILARITY_THRESHOLD:
            return []

        return raw_results

    # ------------------------------------------------------------------
    # Hybrid search (BM25 + RRF)
    # ------------------------------------------------------------------

    def _hybrid_rrf(self, vector_results: list[dict], query: str) -> list[dict]:
        """Merge vector results with BM25 results via Reciprocal Rank Fusion."""
        from rank_bm25 import BM25Okapi  # type: ignore

        texts = [r["text"] for r in vector_results]
        tokenised = [t.lower().split() for t in texts]
        bm25 = BM25Okapi(tokenised)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)

        # Build BM25 ranked list (same items, different order)
        bm25_ranked = sorted(
            [
                dict(item, score=float(score))
                for item, score in zip(vector_results, bm25_scores)
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

        return _rrf_merge([vector_results, bm25_ranked])

    # ------------------------------------------------------------------
    # Reranking (cross-encoder)
    # ------------------------------------------------------------------

    def _rerank(self, candidates: list[dict], query: str) -> list[dict]:
        """Score candidates with a cross-encoder and return sorted results."""
        encoder = _get_cross_encoder()
        pairs = [[query, c["text"]] for c in candidates]
        scores = encoder.predict(pairs)  # type: ignore[union-attr]
        for item, score in zip(candidates, scores):
            item["score"] = float(score)
        return sorted(candidates, key=lambda x: x["score"], reverse=True)
