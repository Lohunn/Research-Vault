"""API integration tests for collections, documents, and chat routes."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.models.db import Collection, Document, Message
from app.models.schemas import CitationSchema, MessageRead


def test_create_and_list_collections(client: TestClient):
    # 1. Create collection
    res = client.post("/collections", json={"name": "Quantum Computing"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Quantum Computing"
    assert "id" in data
    col_id = data["id"]

    # 2. Duplicate name returns 409
    dup_res = client.post("/collections", json={"name": "Quantum Computing"})
    assert dup_res.status_code == 409

    # 3. List collections
    list_res = client.get("/collections")
    assert list_res.status_code == 200
    names = [c["name"] for c in list_res.json()]
    assert "Quantum Computing" in names


def test_upload_and_list_documents(client: TestClient, sample_collection: Collection):
    col_id = str(sample_collection.id)

    # 1. Reject non-PDF file
    fake_txt = io.BytesIO(b"Hello world text file")
    res_txt = client.post(
        f"/collections/{col_id}/documents",
        files={"file": ("test.txt", fake_txt, "text/plain")},
    )
    assert res_txt.status_code == 400

    # 2. Reject upload to non-existent collection
    random_id = str(uuid.uuid4())
    fake_pdf = io.BytesIO(b"%PDF-1.4 mock content")
    res_404 = client.post(
        f"/collections/{random_id}/documents",
        files={"file": ("paper.pdf", fake_pdf, "application/pdf")},
    )
    assert res_404.status_code == 404

    # 3. Successful PDF upload
    with patch("app.api.documents.ingestion_service.ingest", new_callable=AsyncMock):
        fake_pdf2 = io.BytesIO(b"%PDF-1.4 mock content for upload")
        res_upload = client.post(
            f"/collections/{col_id}/documents",
            files={"file": ("paper.pdf", fake_pdf2, "application/pdf")},
        )
        assert res_upload.status_code == 202
        doc_data = res_upload.json()
        assert doc_data["filename"] == "paper.pdf"
        assert doc_data["status"] == "processing"
        assert doc_data["collection_id"] == col_id
        doc_id = doc_data["id"]

        # 4. List documents in collection
        list_res = client.get(f"/collections/{col_id}/documents")
        assert list_res.status_code == 200
        docs = list_res.json()
        assert len(docs) >= 1
        assert any(d["id"] == doc_id for d in docs)

        # 5. Delete document
        del_res = client.delete(f"/documents/{doc_id}")
        assert del_res.status_code == 204

        # 6. Delete again returns 404
        del_404 = client.delete(f"/documents/{doc_id}")
        assert del_404.status_code == 404


def test_chat_nonexistent_collection_returns_404(client: TestClient):
    random_id = str(uuid.uuid4())
    res = client.post(
        f"/collections/{random_id}/chat",
        json={"question": "What is this?", "history": []},
    )
    assert res.status_code == 404


def test_message_read_schema_parses_json_citations():
    """Verify that MessageRead properly decodes JSON-serialized citations from Message DB model."""
    msg = Message(
        id=uuid.uuid4(),
        collection_id=uuid.uuid4(),
        role="assistant",
        content="Here is the answer [1].",
        citations='[{"index": 1, "doc_id": "doc-1", "filename": "paper.pdf", "page": 3, "snippet": "Sample"}]',
    )
    read_obj = MessageRead.model_validate(msg)
    assert len(read_obj.citations) == 1
    assert isinstance(read_obj.citations[0], CitationSchema)
    assert read_obj.citations[0].index == 1
    assert read_obj.citations[0].doc_id == "doc-1"
    assert read_obj.citations[0].filename == "paper.pdf"
    assert read_obj.citations[0].page == 3
    assert read_obj.citations[0].snippet == "Sample"
