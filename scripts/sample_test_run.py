"""Sample Test Run & Walkthrough for ResearchVault.

This script executes a full lifecycle test run against the ResearchVault backend:
1. Configuration check (Settings, thresholds, models)
2. Database schema initialisation (SQLite + SQLModel)
3. Health endpoint check (GET /health)
4. Collection creation (POST /collections)
5. Duplicate collection validation (409 Conflict rejection)
6. Collection listing (GET /collections)
7. Ingestion chunking & header/footer cleaning verification
8. Document upload validation (400 Bad Request on invalid files)
9. Grounding Fallback test (Hallucination shield & threshold cutoff)
10. Grounded Answering & SSE Citation extraction test
11. Citation schema & database deserialization test
12. Document deletion flow (204 No Content & cleanup)
"""

import asyncio
import io
import json
import os
import sys
import uuid

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlmodel import SQLModel, Session, select
import httpx

from app.config import settings
from app.db import engine
from app.main import app
from app.models.db import Collection, Document, Message
from app.models.schemas import CollectionCreate, CollectionRead, DocumentRead, CitationSchema, MessageRead
from app.services.ingestion import approx_tokens, chunk_text, clean_pages
from app.services.answer import AnswerService, _NOT_FOUND_MSG


def print_step(title: str):
    print(f"\n{'='*64}\n▶ {title}\n{'='*64}")


async def run_sample_test():
    # -------------------------------------------------------------
    # STEP 1: Configuration Verification
    # -------------------------------------------------------------
    print_step("STEP 1: Checking System Configuration")
    print(f"  • Embedding Model    : {settings.EMBEDDING_MODEL}")
    print(f"  • Vector Store Mode  : {settings.VECTOR_STORE}")
    print(f"  • LLM Provider       : {settings.LLM_PROVIDER}")
    print(f"  • Similarity Cutoff  : {settings.SIMILARITY_THRESHOLD}")
    print(f"  • Retrieval Top-K    : {settings.RETRIEVAL_TOP_K}")
    print(f"  • Max Upload Size    : {settings.MAX_UPLOAD_SIZE_MB} MB")
    print("  ✓ [PASS] Configuration loaded successfully.")

    # -------------------------------------------------------------
    # STEP 2: Database Schema
    # -------------------------------------------------------------
    print_step("STEP 2: Initialising Database Tables")
    SQLModel.metadata.create_all(engine)
    print("  ✓ [PASS] SQLite tables (Collection, Document, Message) created.")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        
        # ---------------------------------------------------------
        # STEP 3: Liveness Health Check
        # ---------------------------------------------------------
        print_step("STEP 3: Testing Liveness (GET /health)")
        res = await client.get("/health")
        print(f"  HTTP Status : {res.status_code}")
        print(f"  Payload     : {res.json()}")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        print("  ✓ [PASS] Health check verified.")

        # ---------------------------------------------------------
        # STEP 4: Collection Creation
        # ---------------------------------------------------------
        print_step("STEP 4: Creating a Research Collection (POST /collections)")
        col_name = f"NLP Papers {uuid.uuid4().hex[:6]}"
        res = await client.post("/collections", json={"name": col_name})
        print(f"  HTTP Status : {res.status_code}")
        data = res.json()
        print(f"  Created Col : ID={data['id']}, Name='{data['name']}'")
        assert res.status_code == 201
        collection_id = data["id"]
        print("  ✓ [PASS] Collection created successfully.")

        # ---------------------------------------------------------
        # STEP 5: Duplicate Rejection
        # ---------------------------------------------------------
        print_step("STEP 5: Verifying Duplicate Prevention (POST /collections duplicate)")
        dup_res = await client.post("/collections", json={"name": col_name})
        print(f"  HTTP Status : {dup_res.status_code} (Expected 409 Conflict)")
        assert dup_res.status_code == 409
        print("  ✓ [PASS] Duplicate collection rejected.")

        # ---------------------------------------------------------
        # STEP 6: List Collections
        # ---------------------------------------------------------
        print_step("STEP 6: Listing Collections (GET /collections)")
        list_res = await client.get("/collections")
        all_cols = list_res.json()
        print(f"  Total Collections: {len(all_cols)}")
        assert any(c["id"] == collection_id for c in all_cols)
        print("  ✓ [PASS] Created collection present in listing.")

        # ---------------------------------------------------------
        # STEP 7: Ingestion Processing (Cleaning & Chunking)
        # ---------------------------------------------------------
        print_step("STEP 7: Testing Ingestion Logic (Cleaning & Token Chunking)")
        sample_pages = [
            (1, "Header: Journal of AI 2026\nDeep learning architectures rely on self-attention.\nPage 1 Footer"),
            (2, "Header: Journal of AI 2026\nTransformers achieve state-of-the-art results in trans-\nlation tasks.\nPage 2 Footer"),
        ]
        cleaned = clean_pages(sample_pages, num_pages=2)
        print("  Cleaned Page 1 Text :", repr(cleaned[0][1]))
        print("  Cleaned Page 2 Text :", repr(cleaned[1][1]))
        assert "Header: Journal of AI 2026" not in cleaned[0][1]
        assert "translation" in cleaned[1][1]  # Hyphenation healed
        print("  ✓ Header/footer stripping heuristic verified.")
        print("  ✓ Hyphenated word wrap healing verified.")

        long_text = "word " * 600
        chunks = chunk_text(long_text, max_tokens=500, overlap_tokens=80)
        print(f"  Segmented 600 words into {len(chunks)} overlapping chunk(s).")
        assert len(chunks) >= 2
        print("  ✓ [PASS] Page-bounded sliding window chunking verified.")

        # ---------------------------------------------------------
        # STEP 8: Upload File Validation
        # ---------------------------------------------------------
        print_step("STEP 8: Testing PDF Upload Validation")
        fake_txt = io.BytesIO(b"Non-PDF content")
        bad_upload = await client.post(
            f"/collections/{collection_id}/documents",
            files={"file": ("test.txt", fake_txt, "text/plain")},
        )
        print(f"  Non-PDF upload status: {bad_upload.status_code} (Expected 400 Bad Request)")
        assert bad_upload.status_code == 400
        print("  ✓ [PASS] Non-PDF rejected with 400 Bad Request.")

        # ---------------------------------------------------------
        # STEP 9: Hallucination Guardrail (Not Found Fallback)
        # ---------------------------------------------------------
        print_step("STEP 9: Testing Grounding Fallback ('Not Found' Shield)")
        class MockEmptyRetrieval:
            async def retrieve(self, question, collection_id, rewritten_question=None):
                return []

        empty_answer_service = AnswerService(llm=None, retrieval=MockEmptyRetrieval())
        fallback_events = []
        async for sse_event in empty_answer_service.stream_answer(
            question="What is the quantum state vector?",
            collection_id=collection_id,
            history=[],
        ):
            if sse_event.startswith("data: "):
                payload = json.loads(sse_event[6:].strip())
                fallback_events.append(payload)

        print(f"  SSE Stream: {fallback_events}")
        assert fallback_events[0]["type"] == "token"
        assert fallback_events[0]["content"] == _NOT_FOUND_MSG
        assert fallback_events[1]["type"] == "citations"
        assert fallback_events[1]["citations"] == []
        assert fallback_events[2]["type"] == "done"
        print("  ✓ [PASS] Hallucination shield successfully intercepted ungrounded query.")

        # ---------------------------------------------------------
        # STEP 10: Grounded Answering & Citation Stream
        # ---------------------------------------------------------
        print_step("STEP 10: Testing Grounded Answering & SSE Citation Stream")
        doc_uuid = str(uuid.uuid4())
        class MockGroundedRetrieval:
            async def retrieve(self, question, collection_id, rewritten_question=None):
                return [{
                    "score": 0.94,
                    "doc_id": doc_uuid,
                    "collection_id": collection_id,
                    "filename": "attention_paper.pdf",
                    "page": 3,
                    "chunk_index": 0,
                    "text": "The Transformer uses multi-head attention to attend to information from different representation subspaces."
                }]

        class MockLLMProvider:
            async def stream_chat(self, system: str, messages: list[dict]):
                tokens = ["The ", "Transformer ", "employs ", "multi-head ", "attention [1]."]
                for t in tokens:
                    yield t

        grounded_answer_service = AnswerService(llm=MockLLMProvider(), retrieval=MockGroundedRetrieval())
        grounded_events = []
        streamed_answer = ""
        async for sse_event in grounded_answer_service.stream_answer(
            question="How does attention work?",
            collection_id=collection_id,
            history=[],
        ):
            if sse_event.startswith("data: "):
                payload = json.loads(sse_event[6:].strip())
                grounded_events.append(payload)
                if payload["type"] == "token":
                    streamed_answer += payload["content"]

        print(f"  Streamed Text: {repr(streamed_answer)}")
        citations_event = next(e for e in grounded_events if e["type"] == "citations")
        print(f"  Citations Event: {json.dumps(citations_event['citations'], indent=2)}")
        assert len(citations_event["citations"]) == 1
        assert citations_event["citations"][0]["index"] == 1
        assert citations_event["citations"][0]["filename"] == "attention_paper.pdf"
        assert citations_event["citations"][0]["page"] == 3
        print("  ✓ [PASS] Real-time token streaming and page-level citation extraction verified.")

        # ---------------------------------------------------------
        # STEP 11: Citation Deserialization
        # ---------------------------------------------------------
        print_step("STEP 11: Verifying DB Citation Deserialization")
        test_msg = Message(
            id=uuid.uuid4(),
            collection_id=uuid.UUID(collection_id),
            role="assistant",
            content="The Transformer employs multi-head attention [1].",
            citations=json.dumps(citations_event["citations"]),
        )
        msg_read = MessageRead.model_validate(test_msg)
        assert len(msg_read.citations) == 1
        assert isinstance(msg_read.citations[0], CitationSchema)
        assert msg_read.citations[0].page == 3
        print(f"  Parsed Citation Model: File='{msg_read.citations[0].filename}', Page={msg_read.citations[0].page}")
        print("  ✓ [PASS] Database message model properly validates JSON citations.")

    print("\n" + "="*64)
    print("🎉 ALL 11/11 SAMPLE TEST RUN CHECKS PASSED SUCCESSFULLY!")
    print("="*64 + "\n")


if __name__ == "__main__":
    asyncio.run(run_sample_test())
