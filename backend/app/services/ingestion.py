"""Ingestion pipeline: extract text from PDF, clean, chunk, embed, and upsert."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from pathlib import Path
import re
from typing import Any
import uuid

from sqlmodel import Session

from app.config import settings
from app.db import engine
from app.models.db import Document
from app.stores import get_vector_store
from app.stores.vector_store import VectorStore


def approx_tokens(text: str) -> int:
    """Approximate token count (1 token ≈ 0.75 words)."""
    return max(1, int(len(text.split()) / 0.75))


def chunk_text(text: str, max_tokens: int = 500, overlap_tokens: int = 80) -> list[str]:
    """Split text into ~max_tokens chunks with ~overlap_tokens overlap using word-count approximation."""
    words = text.split()
    if not words:
        return []

    max_words = int(max_tokens * 0.75)
    overlap_words = int(overlap_tokens * 0.75)
    if max_words <= 0:
        max_words = 1
    if overlap_words >= max_words:
        overlap_words = max(0, max_words - 1)

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + 1, end - overlap_words)
    return chunks


def clean_pages(pages_raw: list[tuple[int, str]], num_pages: int) -> list[tuple[int, str]]:
    """Clean pages by removing repeated short lines (headers/footers) and fixing hyphenated breaks."""
    header_footer_candidates: set[str] = set()

    # Heuristic: lines <= 60 chars that appear in >= 30% of pages (at least 2 pages)
    if num_pages >= 2:
        line_page_counts: dict[str, int] = defaultdict(int)
        for _, page_text in pages_raw:
            seen_on_page: set[str] = set()
            for line in page_text.splitlines():
                s = line.strip()
                if s and len(s) <= 60:
                    seen_on_page.add(s)
            for s in seen_on_page:
                line_page_counts[s] += 1

        for line, count in line_page_counts.items():
            if count >= 2 and (count / num_pages) >= 0.30:
                header_footer_candidates.add(line)

    cleaned: list[tuple[int, str]] = []
    for page_num, page_text in pages_raw:
        kept_lines = []
        for line in page_text.splitlines():
            s = line.strip()
            if s in header_footer_candidates:
                continue
            kept_lines.append(line)

        text = "\n".join(kept_lines)
        # Fix hyphenated line breaks (e.g. "docu-\n  ment" -> "document")
        text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
        cleaned.append((page_num, text))

    return cleaned


class IngestionService:
    """PDF ingestion pipeline service."""

    _model_cache: dict[str, Any] = {}

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embed_model_name: str | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._embed_model_name = embed_model_name

    @property
    def vector_store(self) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    @property
    def embed_model_name(self) -> str:
        if self._embed_model_name is None:
            self._embed_model_name = settings.EMBEDDING_MODEL
        return self._embed_model_name

    @classmethod
    def get_model(cls, model_name: str) -> Any:
        """Lazy load and cache embedding model."""
        if model_name not in cls._model_cache:
            from sentence_transformers import SentenceTransformer

            cls._model_cache[model_name] = SentenceTransformer(model_name)
        return cls._model_cache[model_name]

    async def ingest(
        self,
        doc_id: uuid.UUID | str,
        file_path: str | None = None,
        collection_id: uuid.UUID | str | None = None,
        filename: str | None = None,
    ) -> None:
        """Ingest a PDF document into the vector store.

        1. Load PDF from uploads/ (or given file_path)
        2. Extract text per page using PyMuPDF (fitz)
        3. Clean repeated headers/footers and fix hyphenated line breaks
        4. Chunk per page without crossing boundaries
        5. Batch embed all chunks with SentenceTransformer
        6. Upsert chunk dicts to vector store
        7. Update Document status to 'ready' and num_pages
        8. On exception: update Document status to 'failed', error_msg and re-raise
        """
        doc_uuid = uuid.UUID(str(doc_id)) if not isinstance(doc_id, uuid.UUID) else doc_id

        # Resolve missing metadata from SQLite if needed
        if file_path is None or collection_id is None or filename is None:
            with Session(engine) as session:
                doc_record = session.get(Document, doc_uuid)
                if doc_record is not None:
                    if file_path is None:
                        file_path = str(Path("uploads") / doc_record.stored_filename)
                    if collection_id is None:
                        collection_id = str(doc_record.collection_id)
                    if filename is None:
                        filename = doc_record.filename

        try:
            # 1 & 2. Extract text per page using PyMuPDF
            import fitz

            pdf_doc = fitz.open(file_path)
            num_pages = len(pdf_doc)
            pages_raw: list[tuple[int, str]] = []
            for page_idx, page in enumerate(pdf_doc, start=1):
                pages_raw.append((page_idx, page.get_text()))
            pdf_doc.close()

            # 3. Clean pages
            cleaned_pages = clean_pages(pages_raw, num_pages)

            # 4. Chunk each page
            chunks: list[dict] = []
            chunk_index = 0
            for page_num, cleaned_text in cleaned_pages:
                page_chunks = chunk_text(cleaned_text, max_tokens=500, overlap_tokens=80)
                for chunk_str in page_chunks:
                    if not chunk_str.strip():
                        continue
                    chunks.append(
                        {
                            "doc_id": str(doc_uuid),
                            "collection_id": str(collection_id or ""),
                            "filename": str(filename or ""),
                            "page": page_num,
                            "chunk_index": chunk_index,
                            "text": chunk_str,
                        }
                    )
                    chunk_index += 1

            # 5. Batch embed chunks
            if chunks:
                loop = asyncio.get_event_loop()
                texts = [c["text"] for c in chunks]

                def _embed_all() -> list[list[float]]:
                    model = self.get_model(self.embed_model_name)
                    embeddings = model.encode(texts, normalize_embeddings=True)
                    if hasattr(embeddings, "tolist"):
                        return embeddings.tolist()
                    return [list(e) for e in embeddings]

                vectors = await loop.run_in_executor(None, _embed_all)
                for i, vec in enumerate(vectors):
                    chunks[i]["vector"] = vec

                # 6. Upsert to vector store
                await self.vector_store.upsert(chunks)

            # 7. Update Document status="ready" in DB
            with Session(engine) as session:
                doc_record = session.get(Document, doc_uuid)
                if doc_record is not None:
                    doc_record.status = "ready"
                    doc_record.num_pages = num_pages
                    doc_record.error_msg = None
                    session.add(doc_record)
                    session.commit()

        except Exception as e:
            # 8. On exception: status="failed" and re-raise
            with Session(engine) as session:
                doc_record = session.get(Document, doc_uuid)
                if doc_record is not None:
                    doc_record.status = "failed"
                    doc_record.error_msg = str(e)
                    session.add(doc_record)
                    session.commit()
            raise
