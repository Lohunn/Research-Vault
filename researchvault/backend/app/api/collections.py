from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.db import engine
from app.models.db import Collection
from app.models.schemas import CollectionCreate, CollectionRead

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionRead, status_code=201)
def create_collection(body: CollectionCreate) -> CollectionRead:
    with Session(engine) as session:
        existing = session.exec(
            select(Collection).where(Collection.name == body.name)
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Collection name already exists")
        col = Collection(name=body.name)
        session.add(col)
        session.commit()
        session.refresh(col)
        return CollectionRead.model_validate(col)


@router.get("", response_model=list[CollectionRead])
def list_collections() -> list[CollectionRead]:
    with Session(engine) as session:
        cols = session.exec(select(Collection)).all()
        return [CollectionRead.model_validate(c) for c in cols]
