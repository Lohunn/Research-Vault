from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.config import settings  # noqa: F401 — re-exported for convenience
from app.db import engine  # noqa: F401 — re-exported for convenience


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all SQLite tables on startup
    SQLModel.metadata.create_all(engine)
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title="ResearchVault API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api import collections, documents, chat  # noqa: E402

app.include_router(collections.router)
app.include_router(documents.router)
app.include_router(chat.router)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
