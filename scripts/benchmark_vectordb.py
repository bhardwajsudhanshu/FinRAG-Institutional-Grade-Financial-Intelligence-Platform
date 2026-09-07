"""Vector-DB benchmark harness (ADR-005, exp_050+).

Measures STORE performance with quality frozen: upserts the eval set's
naive chunks (mock embeddings — free, deterministic; the store never
sees a real embedding, which is correct because latency/parity don't
depend on embedding provenance), then times per-question queries and
checks parity against brute-force InMemoryIndex.

Usage:
    # Preview (mock embeddings, Qdrant :memory:, $0, ~3 min):
    EMBEDDER_BACKEND=mock uv run python scripts/benchmark_vectordb.py --out results/benchmarks/qdrant_preview.json

    # Live docker Qdrant (needs Docker Desktop up):
    EMBEDDER_BACKEND=mock uv run python scripts/benchmark_vectordb.py --qdrant-url http://localhost:6333 --out results/benchmarks/qdrant_docker.json

Output JSON: {n_chunks, upsert_s, latencies_ms per backend, parity, ...}.
Canonical benchmark rows for experiments.csv come from full eval runs
(STEP_017+), not from this script — this is the timing instrument.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from finrag.chunking import chunk_sections_by_strategy  # noqa: E402
from finrag.config import get_settings  # noqa: E402
from finrag.data.parse_sections import parse_filing  # noqa: E402
from finrag.embeddings import get_embedder  # noqa: E402
from finrag.retrieval import InMemoryIndex  # noqa: E402
from finrag.vectordb import QdrantBackend  # noqa: E402


def _load_eval_chunks() -> tuple[list, list[dict]]:
    """Naive chunks for the 20 eval filings + QA rows (question text only)."""
    import pandas as pd

    settings = get_settings()
    qa = [json.loads(line) for line in
          Path("data/eval/qa_pairs.jsonl").read_text(encoding="utf-8").splitlines()
          if line.strip()]
    manifest = pd.read_parquet(settings.data_raw_dir / "filings.parquet")
    by_key = {(r["ticker"], str(r["filing_date"])): r for _, r in manifest.iterrows()}
    chunks = []
    for ticker, filing_date in {(q["source_ticker"], q["source_filing_date"]) for q in qa}:
        row = by_key[(ticker, filing_date)]
        sections = parse_filing(Path(row["local_path"]).read_text(encoding="utf-8"))
        chunks.extend(chunk_sections_by_strategy(
            "naive", sections=sections, ticker=ticker, filing_date=filing_date,
            fiscal_year=int(row.get("fiscal_year", 0)),
            accession_number=row.get("accession_number", "")))
    return chunks, qa


def _percentile(data: list[float], p: float) -> float:
    s = sorted(data)
    if not s:
        return 0.0
    k = (len(s) - 1) * p / 100.0
    import math
    f, c = math.floor(k), math.ceil(k)
    return s[int(k)] if f == c else s[f] * (c - k) + s[c] * (k - f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qdrant-url", default=":memory:",
                        help="Qdrant location (:memory: or http://host:6333)")
    parser.add_argument("--out", type=Path, default=Path("results/benchmarks/qdrant_preview.json"))
    parser.add_argument("--collection", default="finrag_bench")
    args = parser.parse_args()

    chunks, qa = _load_eval_chunks()
    print(f"[bench] {len(chunks)} chunks, {len(qa)} questions")
    embedder = get_embedder()
    t0 = time.perf_counter()
    vectors = embedder.embed_batch([c.text for c in chunks])
    print(f"[bench] embedded in {time.perf_counter() - t0:.1f}s ({type(embedder).__name__})")

    mem = InMemoryIndex()
    for c, v in zip(chunks, vectors, strict=True):
        mem.add(c, v)

    t0 = time.perf_counter()
    qdb = QdrantBackend(dim=embedder.dim, collection=args.collection,
                        location=args.qdrant_url)
    qdb.upsert([c.chunk_id for c in chunks], vectors,
               payloads=[{"ticker": c.metadata.get("ticker", ""),
                          "section_id": c.metadata.get("section_id", "")} for c in chunks])
    upsert_s = time.perf_counter() - t0
    print(f"[bench] qdrant upsert {len(chunks)} in {upsert_s:.1f}s")

    mem_lat, qdb_lat, top1_agree, set_overlap = [], [], 0, []
    questions = [q["question"] for q in qa]
    qvecs = embedder.embed_batch(questions)
    for qv in qvecs:
        t = time.perf_counter()
        exp_ids = [c.chunk_id for c, _ in mem.query(qv, top_k=5)]
        mem_lat.append((time.perf_counter() - t) * 1000)
        t = time.perf_counter()
        got_ids = [cid for cid, _ in qdb.query(qv, top_k=5)]
        qdb_lat.append((time.perf_counter() - t) * 1000)
        top1_agree += int(bool(got_ids) and bool(exp_ids) and got_ids[0] == exp_ids[0])
        set_overlap.append(len(set(got_ids) & set(exp_ids)) / max(1, len(exp_ids)))
    qdb.close()

    result = {
        "n_chunks": len(chunks),
        "n_questions": len(qa),
        "qdrant_location": args.qdrant_url,
        "embedder": type(embedder).__name__,
        "upsert_s": round(upsert_s, 2),
        "in_memory": {"p50_ms": round(_percentile(mem_lat, 50), 2),
                      "p95_ms": round(_percentile(mem_lat, 95), 2)},
        "qdrant": {"p50_ms": round(_percentile(qdb_lat, 50), 2),
                   "p95_ms": round(_percentile(qdb_lat, 95), 2)},
        "parity_top1_rate": round(top1_agree / len(qa), 4),
        "parity_set_overlap_mean": round(statistics.fmean(set_overlap), 4),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
