from abc import ABC, abstractmethod

from app.config import settings


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: list[dict]) -> None: ...

    @abstractmethod
    async def search(
        self, query_vector: list[float], collection_id: str, top_k: int
    ) -> list[dict]: ...

    @abstractmethod
    async def delete_by_doc_id(self, doc_id: str) -> None: ...


def get_vector_store() -> VectorStore:
    """Return the configured VectorStore instance based on VECTOR_STORE setting."""
    if settings.VECTOR_STORE == "qdrant":
        from app.stores.qdrant_store import QdrantStore

        return QdrantStore(
            url=settings.QDRANT_URL,
            collection_prefix=settings.QDRANT_COLLECTION_PREFIX,
        )
    elif settings.VECTOR_STORE == "chroma":
        from app.stores.chroma_store import ChromaStore

        return ChromaStore(path=settings.CHROMA_PATH)
    else:
        raise ValueError(f"Unsupported VECTOR_STORE: {settings.VECTOR_STORE!r}")
