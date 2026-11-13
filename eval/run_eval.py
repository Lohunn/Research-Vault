"""
ResearchVault Evaluation Script
================================
Usage:
    python eval/run_eval.py \\
        --api http://localhost:8000 \\
        --collection-id <UUID> \\
        --questions eval/questions.json \\
        [--top-k 5] \\
        [--output eval/results.json]

Outputs:
    Hit@K   — fraction of questions where expected_doc appears in top-K citations
    MRR     — Mean Reciprocal Rank across all questions
    Latency p50 / p95 (milliseconds)
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    sys.exit("httpx is required: pip install httpx")


# ---------------------------------------------------------------------------
# SSE stream reader
# ---------------------------------------------------------------------------

def _parse_sse_stream(raw: str) -> list[dict[str, Any]]:
    """Parse a raw SSE response body into a list of data payloads.

    The backend streams newline-delimited Server-Sent Events of the form:
        data: {"type": "token", "content": "..."}\n\n
        data: {"type": "citations", "citations": [...]}\n\n
        data: [DONE]\n\n

    Returns a list of parsed JSON dicts (non-JSON lines such as [DONE] are
    skipped).
    """
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload in ("", "[DONE]"):
                continue
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                pass  # ignore malformed lines
    return events


def _extract_citations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the citations list from the SSE event stream.

    The backend emits a single event of the form:
        {"type": "citations", "citations": [{...}, ...]}

    If no such event is found, return an empty list.
    """
    for event in events:
        if event.get("type") == "citations":
            return event.get("citations", [])
    # Fallback: some backends inline citations in every token event
    for event in events:
        if "citations" in event:
            return event["citations"]
    return []


# ---------------------------------------------------------------------------
# Hit@K and reciprocal rank helpers
# ---------------------------------------------------------------------------

def _compute_hit_at_k(
    citations: list[dict[str, Any]],
    expected_doc: str,
    k: int = 5,
) -> bool:
    """Return True if *expected_doc* appears in the first *k* citations."""
    for citation in citations[:k]:
        filename = citation.get("filename", "")
        if expected_doc.lower() in filename.lower():
            return True
    return False


def _compute_reciprocal_rank(
    citations: list[dict[str, Any]],
    expected_doc: str,
) -> float:
    """Return 1/rank of the first citation matching *expected_doc*, or 0."""
    for rank, citation in enumerate(citations, start=1):
        filename = citation.get("filename", "")
        if expected_doc.lower() in filename.lower():
            return 1.0 / rank
    return 0.0


# ---------------------------------------------------------------------------
# Core evaluation loop
# ---------------------------------------------------------------------------

async def run_eval(
    api_url: str,
    collection_id: str,
    questions_path: str,
    top_k: int = 5,
    output_path: str | None = None,
) -> None:
    questions_file = Path(questions_path)
    if not questions_file.exists():
        sys.exit(f"Questions file not found: {questions_path}")

    questions: list[dict[str, Any]] = json.loads(questions_file.read_text(encoding="utf-8"))
    if not questions:
        sys.exit("Questions file is empty.")

    chat_url = f"{api_url.rstrip('/')}/collections/{collection_id}/chat"
    results: list[dict[str, Any]] = []

    print(f"Evaluating {len(questions)} questions against collection {collection_id}")
    print(f"Endpoint: {chat_url}\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, q in enumerate(questions, start=1):
            question_text: str = q["question"]
            expected_doc: str = q.get("expected_doc", "")
            expected_page: int = q.get("expected_page", -1)

            print(f"[{i:2d}/{len(questions)}] {question_text[:70]!r} ...", end=" ", flush=True)

            start = time.perf_counter()

            # POST to the chat endpoint and read the FULL SSE stream
            # (non-streaming mode: we wait for the entire response body).
            try:
                response = await client.post(
                    chat_url,
                    json={"question": question_text, "history": []},
                    headers={"Accept": "text/event-stream"},
                )
                response.raise_for_status()
                raw_body = response.text
            except httpx.HTTPStatusError as exc:
                print(f"HTTP {exc.response.status_code} error — skipping")
                results.append({
                    "question": question_text,
                    "expected_doc": expected_doc,
                    "hit": False,
                    "rr": 0.0,
                    "latency": time.perf_counter() - start,
                    "error": str(exc),
                })
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc} — skipping")
                results.append({
                    "question": question_text,
                    "expected_doc": expected_doc,
                    "hit": False,
                    "rr": 0.0,
                    "latency": time.perf_counter() - start,
                    "error": str(exc),
                })
                continue

            latency = time.perf_counter() - start

            events = _parse_sse_stream(raw_body)
            citations = _extract_citations(events)

            hit = _compute_hit_at_k(citations, expected_doc, k=top_k)
            rr = _compute_reciprocal_rank(citations, expected_doc)

            status = "✓ HIT" if hit else "✗ MISS"
            print(f"{status}  rr={rr:.3f}  lat={latency*1000:.0f}ms  citations={len(citations)}")

            results.append({
                "question": question_text,
                "expected_doc": expected_doc,
                "expected_page": expected_page,
                "hit": hit,
                "rr": rr,
                "latency": latency,
                "top_citations": [c.get("filename", "") for c in citations[:top_k]],
            })

    # ---------------------------------------------------------------------------
    # Aggregate metrics
    # ---------------------------------------------------------------------------
    if not results:
        print("\nNo results to aggregate.")
        return

    hits = [r["hit"] for r in results]
    rrs = [r["rr"] for r in results]
    latencies = sorted(r["latency"] for r in results)

    hit_at_k = sum(hits) / len(hits) * 100
    mrr = sum(rrs) / len(rrs)

    n = len(latencies)
    lat_p50 = statistics.median(latencies) * 1000
    lat_p95 = latencies[min(int(n * 0.95), n - 1)] * 1000

    print("\n" + "=" * 50)
    print(f"Hit@{top_k}:       {hit_at_k:.1f}%")
    print(f"MRR:          {mrr:.3f}")
    print(f"Latency p50:  {lat_p50:.0f} ms")
    print(f"Latency p95:  {lat_p95:.0f} ms")
    print(f"Questions:    {len(results)}")
    print("=" * 50)

    if output_path:
        summary = {
            "collection_id": collection_id,
            "num_questions": len(results),
            f"hit_at_{top_k}": round(hit_at_k, 2),
            "mrr": round(mrr, 4),
            "latency_p50_ms": round(lat_p50, 1),
            "latency_p95_ms": round(lat_p95, 1),
            "results": results,
        }
        Path(output_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nDetailed results written to: {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate ResearchVault retrieval quality (Hit@K, MRR, latency)."
    )
    parser.add_argument(
        "--api",
        default="http://localhost:8000",
        help="Base URL of the ResearchVault API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--collection-id",
        required=True,
        metavar="UUID",
        help="UUID of the collection to query",
    )
    parser.add_argument(
        "--questions",
        default="eval/questions.json",
        metavar="PATH",
        help="Path to the questions JSON file (default: eval/questions.json)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        metavar="K",
        help="Compute Hit@K (default: 5)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Optional path to write detailed JSON results",
    )
    args = parser.parse_args()

    asyncio.run(
        run_eval(
            api_url=args.api,
            collection_id=args.collection_id,
            questions_path=args.questions,
            top_k=args.top_k,
            output_path=args.output,
        )
    )


if __name__ == "__main__":
    main()
