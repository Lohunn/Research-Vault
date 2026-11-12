"""ChromaDB-backed VectorStore implementation."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from app.stores.vector_store import VectorStore


class ChromaStore(VectorStore):
    """Local fallback vector store backed by ChromaDB."""

    def __init__(self, path: str | None = None, collection_prefix: str = "rv_") -> None:
        import chromadb
        from app.config import settings

        self.path = path or settings.CHROMA_PATH
        self.collection_prefix = collection_prefix
        self._client = chromadb.PersistentClient(path=self.path)

    def _col_name(self, collection_id: str) -> str:
        clean_id = str(collection_id).replace("-", "_")
        return f"{self.collection_prefix}{clean_id}"

    async def upsert(self, chunks: list[dict]) -> None:
        """Upsert chunk dicts into ChromaDB."""
        if not chunks:
            return

        loop = asyncio.get_event_loop()

        def _do_upsert() -> None:
            by_col: dict[str, list[dict]] = defaultdict(list)
            for chunk in chunks:
                by_col[str(chunk["collection_id"])].append(chunk)

            for col_id, col_chunks in by_col.items():
                col_name = self._col_name(col_id)
                collection = self._client.get_or_create_collection(
                    name=col_name,
                    metadata={"hnsw:space": "cosine"},
                )
                ids = [
                    f"{c['doc_id']}-{c['chunk_index']}"
                    for c in col_chunks
                ]
                embeddings = [c["vector"] for c in col_chunks]
                documents = [c.get("text", "") for c in col_chunks]
                metadatas = [
                    {
                        "doc_id": str(c["doc_id"]),
                        "collection_id": str(c["collection_id"]),
                        "filename": str(c.get("filename", "")),
                        "page": int(c.get("page", 1)),
                        "chunk_index": int(c.get("chunk_index", 0)),
                    }
                    for c in col_chunks
                ]
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )

        await loop.run_in_executor(None, _do_upsert)

    async def search(
        self, query_vector: list[float], collection_id: str, top_k: int = 20
    ) -> list[dict]:
        """Search ChromaDB collection for nearest neighbors."""
        loop = asyncio.get_event_loop()

        def _do_search() -> list[dict]:
            col_name = self._col_name(collection_id)
            try:
                collection = self._client.get_collection(name=col_name)
            except Exception:
                return []

            res = collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where={"collection_id": str(collection_id)},
                include=["metadatas", "documents", "distances"],
            )
            if not res or not res.get("ids") or not res["ids"][0]:
                return []

            ids = res["ids"][0]
            distances = res.get("distances", [[]])[0] if res.get("distances") else []
            metas = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
            docs = res.get("documents", [[]])[0] if res.get("documents") else []

            hits = []
            for i in range(len(ids)):
                meta = metas[i] if i < len(metas) and metas[i] is not None else {}
                doc_text = docs[i] if i < len(docs) and docs[i] is not None else ""
                dist = distances[i] if i < len(distances) and distances[i] is not None else 1.0
                # Cosine distance: similarity = 1 - distance
                score = 1.0 - dist
                hits.append(
                    {
                        "score": float(score),
                        "doc_id": meta.get("doc_id"),
                        "collection_id": meta.get("collection_id"),
                        "filename": meta.get("filename"),
                        "page": meta.get("page"),
                        "chunk_index": meta.get("chunk_index"),
                        "text": doc_text,
                    }
                )
            return hits

        return await loop.run_in_executor(None, _do_search)

    async def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete points where metadata doc_id == doc_id."""
        loop = asyncio.get_event_loop()

        def _do_delete() -> None:
            cols = self._client.list_collections()
            for col_obj in cols:
                name = col_obj.name if hasattr(col_obj, "name") else str(col_obj)
                if name.startswith(self.collection_prefix):
                    try:
                        col = self._client.get_collection(name=name)
                        col.delete(where={"doc_id": str(doc_id)})
                    except Exception:
                        pass

        await loop.run_in_executor(None, _do_delete)
