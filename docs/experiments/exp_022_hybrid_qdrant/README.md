# exp_022_hybrid_qdrant

## Hypothesis

Hybrid retrieval over live Qdrant reproduces hybrid over brute-force
exactly (parity 1.0 at the store level, STEP_017) — so end-to-end quality
should match exp_021 within noise while per-Q retrieval latency drops
~40×. This is the production configuration candidate: naive chunks +
hybrid RRF + Qdrant dense side.

## Setup

- **Chunker**: `naive` (same 4447 chunks)
- **Retrieval**: `hybrid` (dense top-20 + BM25 top-20 → RRF k=60 → top-5)
- **Dense store**: live Qdrant (`finrag_eval` collection, recreated per run) instead of brute-force
- **Generator / judge**: unchanged. top_k=5, eval v1 139 Q.

## What changes vs. exp_021

One variable only: the dense side's store (brute-force → Qdrant). Same
chunks, same vectors, same BM25 side, same generator. Any metric delta is
store effect (expected: ~zero on quality, large on latency).

## Evaluation

Smoke (~2.5 min, AAPL only — STEP_018):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid VECTORDB_BACKEND=qdrant uv run python -m finrag.cli.eval --exp exp_022_hybrid_qdrant --limit 6 --smoke
```

Full (~50 min — STEP_019):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid VECTORDB_BACKEND=qdrant uv run python -m finrag.cli.eval --exp exp_022_hybrid_qdrant
```

Parity bar: per-Q retrieved sets ≈ exp_021 (compare `retrieved_chunk_ids`
across the two per-question files); metrics within noise of exp_021
(cr 0.8843, content 0.8129).
