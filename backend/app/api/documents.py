from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models.db import Collection, Document
from app.models.schemas import DocumentRead
from app.services.ingestion import IngestionService
from app.stores import get_vector_store

router = APIRouter(tags=["documents"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ingestion_service = IngestionService()


@router.post(
    "/collections/{collection_id}/documents",
    response_model=DocumentRead,
    status_code=202,
)
async def upload_document(
    collection_id: uuid.UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> DocumentRead:
    # Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Validate file size
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    # Check collection exists before saving file
    with Session(engine) as session:
        col = session.get(Collection, collection_id)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Persist to disk with UUID filename
        doc_id = uuid.uuid4()
        stored_filename = f"{doc_id}.pdf"
        dest = UPLOAD_DIR / stored_filename
        dest.write_bytes(contents)

        doc = Document(
            id=doc_id,
            collection_id=collection_id,
            filename=file.filename or stored_filename,
            stored_filename=stored_filename,
            status="processing",
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        result = DocumentRead.model_validate(doc)

    # Fire background ingestion
    background_tasks.add_task(
        ingestion_service.ingest,
        doc_id=str(doc_id),
        file_path=str(dest),
        collection_id=str(collection_id),
        filename=file.filename or stored_filename,
    )

    return result


@router.get(
    "/collections/{collection_id}/documents",
    response_model=list[DocumentRead],
)
def list_documents(collection_id: uuid.UUID) -> list[DocumentRead]:
    with Session(engine) as session:
        docs = session.exec(
            select(Document).where(Document.collection_id == collection_id)
        ).all()
        return [DocumentRead.model_validate(d) for d in docs]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID) -> None:
    with Session(engine) as session:
        doc = session.get(Document, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete vectors from vector store
        vector_store = get_vector_store()
        await vector_store.delete_by_doc_id(str(document_id))

        # Delete file from disk if exists
        file_path = UPLOAD_DIR / doc.stored_filename
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass

        session.delete(doc)
        session.commit()
