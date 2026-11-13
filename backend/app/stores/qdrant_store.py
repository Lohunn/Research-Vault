"""Qdrant-backed VectorStore implementation."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from typing import Any

from app.stores.vector_store import VectorStore

DEFAULT_VECTOR_SIZE = 384


class QdrantStore(VectorStore):
    """Qdrant-backed vector store implementing VectorStore ABC."""

    def __init__(self, url: str, collection_prefix: str = "rv_") -> None:
        from qdrant_client import QdrantClient

        self.url = url
        self.collection_prefix = collection_prefix
        self._client = QdrantClient(url=url)

    def _col_name(self, collection_id: str) -> str:
        return f"{self.collection_prefix}{collection_id}"

    def _ensure_collection(self, collection_name: str, vector_size: int = DEFAULT_VECTOR_SIZE) -> None:
        from qdrant_client.http import models as qmodels

        existing = {c.name for c in self._client.get_collections().collections}
        if collection_name not in existing:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )

    async def upsert(self, chunks: list[dict]) -> None:
        """Upsert a list of chunk dicts into Qdrant.

        Each chunk dict has:
            doc_id, collection_id, filename, page, chunk_index, text, vector (list[float])
        """
        if not chunks:
            return

        from qdrant_client.http import models as qmodels

        loop = asyncio.get_event_loop()

        def _do_upsert() -> None:
            by_col: dict[str, list[dict]] = defaultdict(list)
            for chunk in chunks:
                by_col[str(chunk["collection_id"])].append(chunk)

            for col_id, col_chunks in by_col.items():
                col_name = self._col_name(col_id)
                vec_size = (
                    len(col_chunks[0]["vector"])
                    if col_chunks and "vector" in col_chunks[0]
                    else DEFAULT_VECTOR_SIZE
                )
                self._ensure_collection(col_name, vec_size)

                points = []
                for chunk in col_chunks:
                    point_id = str(
                        uuid.uuid5(
                            uuid.NAMESPACE_DNS,
                            f"{chunk['doc_id']}-{chunk['chunk_index']}",
                        )
                    )
                    points.append(
                        qmodels.PointStruct(
                            id=point_id,
                            vector=chunk["vector"],
                            payload={
                                "doc_id": str(chunk["doc_id"]),
                                "collection_id": str(chunk["collection_id"]),
                                "filename": chunk.get("filename", ""),
                                "page": int(chunk.get("page", 1)),
                                "chunk_index": int(chunk.get("chunk_index", 0)),
                                "text": chunk.get("text", ""),
                            },
                        )
                    )
                self._client.upsert(collection_name=col_name, points=points)

        await loop.run_in_executor(None, _do_upsert)

    async def search(
        self, query_vector: list[float], collection_id: str, top_k: int = 20
    ) -> list[dict]:
        """Search vector store for chunks matching collection_id."""
        from qdrant_client.http import models as qmodels

        loop = asyncio.get_event_loop()

        def _do_search() -> list[dict]:
            col_name = self._col_name(collection_id)
            existing = {c.name for c in self._client.get_collections().collections}
            if col_name not in existing:
                return []

            results = self._client.search(
                collection_name=col_name,
                query_vector=query_vector,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="collection_id",
                            match=qmodels.MatchValue(value=str(collection_id)),
                        )
                    ]
                ),
                limit=top_k,
                with_payload=True,
            )
            hits = []
            for r in results:
                p = r.payload or {}
                hits.append(
                    {
                        "score": float(r.score),
                        "doc_id": p.get("doc_id"),
                        "collection_id": p.get("collection_id"),
                        "filename": p.get("filename"),
                        "page": p.get("page"),
                        "chunk_index": p.get("chunk_index"),
                        "text": p.get("text"),
                    }
                )
            return hits

        return await loop.run_in_executor(None, _do_search)

    async def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all points where payload.doc_id == doc_id."""
        from qdrant_client.http import models as qmodels

        loop = asyncio.get_event_loop()

        def _do_delete() -> None:
            collections = self._client.get_collections().collections
            for col in collections:
                if col.name.startswith(self.collection_prefix):
                    try:
                        self._client.delete(
                            collection_name=col.name,
                            points_selector=qmodels.FilterSelector(
                                filter=qmodels.Filter(
                                    must=[
                                        qmodels.FieldCondition(
                                            key="doc_id",
                                            match=qmodels.MatchValue(value=str(doc_id)),
                                        )
                                    ]
                                )
                            ),
                        )
                    except Exception:
                        pass

        await loop.run_in_executor(None, _do_delete)
