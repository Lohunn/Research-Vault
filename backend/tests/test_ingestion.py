"""Unit and integration tests for IngestionService, chunking, and cleaning."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion import (
    IngestionService,
    approx_tokens,
    chunk_text,
    clean_pages,
)


def test_approx_tokens():
    text = "word " * 75
    # 75 words / 0.75 = 100 approx tokens
    tokens = approx_tokens(text)
    assert tokens == 100


def test_chunk_text():
    text = "word " * 1000
    chunks = chunk_text(text, max_tokens=500, overlap_tokens=80)
    assert len(chunks) > 1
    # Check all chunks have text
    for ch in chunks:
        assert len(ch) > 0


def test_clean_pages():
    # 3 pages with repeated header
    pages_raw = [
        (1, "Header line\nThis is content on page one.\nFooter note"),
        (2, "Header line\nThis is content on page two.\nFooter note"),
        (3, "Header line\nThis is docu-\nment with content on page three.\nFooter note"),
    ]
    cleaned = clean_pages(pages_raw, num_pages=3)
    assert len(cleaned) == 3

    # Header and Footer should be removed
    for _, text in cleaned:
        assert "Header line" not in text
        assert "Footer note" not in text

    # Hyphenation should be fixed: docu-\nment -> document
    assert "document" in cleaned[2][1]


@pytest.mark.asyncio
async def test_ingest_pipeline(tmp_path):
    """Test full IngestionService.ingest pipeline with mocked vector store and embedder."""
    # Create a tiny 2-page PDF
    pdf_path = tmp_path / "test_doc.pdf"

    # Mock or use PyMuPDF fitz
    mock_pdf_doc = MagicMock()
    mock_pdf_doc.__len__.return_value = 2

    mock_page_1 = MagicMock()
    mock_page_1.get_text.return_value = "Page one text content about artificial intelligence."
    mock_page_2 = MagicMock()
    mock_page_2.get_text.return_value = "Page two text content about retrieval augmented generation."
    mock_pdf_doc.__iter__.return_value = [mock_page_1, mock_page_2]

    # Mock vector store
    mock_vector_store = MagicMock()
    mock_vector_store.upsert = AsyncMock()

    doc_id = uuid.uuid4()
    collection_id = uuid.uuid4()

    service = IngestionService(
        vector_store=mock_vector_store,
        embed_model_name="BAAI/bge-small-en-v1.5",
    )

    # Mock sentence transformer model
    mock_model = MagicMock()
    mock_embeddings = MagicMock()
    mock_embeddings.tolist.return_value = [[0.1] * 384, [0.2] * 384]
    mock_model.encode.return_value = mock_embeddings

    with patch("fitz.open", return_value=mock_pdf_doc), patch.object(
        IngestionService, "get_model", return_value=mock_model
    ), patch("app.services.ingestion.Session") as mock_session_cls:
        # Mock DB session and document
        mock_session = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.stored_filename = "test_doc.pdf"
        mock_session.get.return_value = mock_doc
        mock_session_cls.return_value.__enter__.return_value = mock_session

        await service.ingest(
            doc_id=doc_id,
            file_path=str(pdf_path),
            collection_id=collection_id,
            filename="test_doc.pdf",
        )

        # Assert upsert called
        assert mock_vector_store.upsert.called
        upserted_chunks = mock_vector_store.upsert.call_args[0][0]
        assert len(upserted_chunks) >= 2

        # Check chunk structure
        pages = [c["page"] for c in upserted_chunks]
        assert 1 in pages
        assert 2 in pages

        for c in upserted_chunks:
            assert c["doc_id"] == str(doc_id)
            assert c["collection_id"] == str(collection_id)
            assert c["filename"] == "test_doc.pdf"
            assert "vector" in c
            assert len(c["vector"]) == 384

        # Assert DB record updated to ready
        assert mock_doc.status == "ready"
        assert mock_doc.num_pages == 2


@pytest.mark.asyncio
async def test_ingest_failure_updates_status():
    """Test that ingestion errors set Document status to failed and re-raise."""
    mock_vector_store = MagicMock()
    service = IngestionService(vector_store=mock_vector_store)

    doc_id = uuid.uuid4()

    with patch("fitz.open", side_effect=RuntimeError("Corrupt PDF")), patch(
        "app.services.ingestion.Session"
    ) as mock_session_cls:
        mock_session = MagicMock()
        mock_doc = MagicMock()
        mock_session.get.return_value = mock_doc
        mock_session_cls.return_value.__enter__.return_value = mock_session

        with pytest.raises(RuntimeError, match="Corrupt PDF"):
            await service.ingest(
                doc_id=doc_id,
                file_path="nonexistent.pdf",
                collection_id=uuid.uuid4(),
                filename="nonexistent.pdf",
            )

        assert mock_doc.status == "failed"
        assert "Corrupt PDF" in mock_doc.error_msg
