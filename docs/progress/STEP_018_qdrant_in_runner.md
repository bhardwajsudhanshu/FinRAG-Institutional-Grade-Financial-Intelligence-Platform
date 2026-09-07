# STEP_018 — Qdrant in the eval path (hybrid end-to-end)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Dense side runs on live Qdrant inside the real pipeline; prove end-to-end parity path before the full run. No ledger change.
- **Roadmap phase:** Vector-DB benchmark (runner wiring; Qdrant approved STEP_017)

### 1. Why
STEP_017 proved store-level parity (same vectors → same ranking) on an
isolated harness. That doesn't prove the *pipeline* is store-agnostic:
the runner embeds, upserts, maps ids→chunks, and fuses with BM25. One
wiring bug (wrong collection, id mismatch, score misuse) silently shifts
every metric. exp_022 exists to catch exactly that, holding everything
else equal to exp_021.

### 2. What changed (files — this commit)
- `finrag/config.py` — `vectordb_backend` redefined (`"chroma"` default was dead — never implemented/read anywhere; verified by grep): `"in-memory"` (default, frozen behavior) | `"qdrant"`, plus `qdrant_url`. `.env.example` updated to match.
- `finrag/vectordb/qdrant_backend.py` — NEW `QdrantDenseIndex` adapter (same `.query` interface as `InMemoryIndex`, id→Chunk mapping, missing ids skipped defensively); exported.
- `finrag/eval/ragas_runner.py` — `_build_dense_index()` (in-memory vs Qdrant branch, loud ValueError otherwise); bundle carries `vectordb_backend`; per-Q record gains the field; `n_chunks` from bundle (unchanged value).
- `finrag/cli/eval.py` — prints `Retrieval: <strategy> over <vectordb>`.
- `tests/test_vectordb.py` — 3 adapter tests (`:memory:`, offline) + unknown-backend rejection.
- `docs/experiments/exp_022_hybrid_qdrant/{README,config.yaml,analysis.md}` — NEW scaffold (one-variable-vs-exp_021 design, parity bar).
- `docs/progress/STEP_018_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (6 rows), leaderboard, eval set, retrieval math, BM25 path.
- NOT committed: `results/smoke/exp_022_hybrid_qdrant_*/` (ephemeral).

### 3. How it works
`build_index_for_qa_pairs` builds the dense side per `vectordb_backend`:
in-memory → `build_index` (as before); qdrant → embed batch → upsert to
recreated `finrag_eval` collection on `qdrant_url` → wrap adapter. BM25
side and RRF fusion untouched — `retrieve_with_strategy` can't tell which
dense index it holds (same interface). Collection recreated per run
(serial nightly assumption, noted in code).

### 4. How to verify
```bash
uv run pytest tests/test_vectordb.py tests/test_retrieval.py tests/test_generation.py tests/test_chunking.py tests/eval/test_metrics.py tests/eval/test_ragas_runner.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid VECTORDB_BACKEND=qdrant uv run python -m finrag.cli.eval --exp exp_022_hybrid_qdrant --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 100 passed (3 new). Ruff: no new issues (all flags pre-existing classes).
- Smoke 2026-09-07 (6 Q, AAPL naive 97, live Qdrant, $0.0017): content 0.833 (5/6 — IDENTICAL to in-memory hybrid smoke incl. same only-miss q_0005), cr=1.0/fa=0.8963, index 27.6s. Per-Q rows carry hybrid+qdrant.
- Config note (action taken): live `.env` (gitignored) still had `VECTORDB_BACKEND=chroma`, which is now a loud ValueError — updated to `in-memory` (= frozen behavior) + `QDRANT_URL` default. Without this, every future run without an explicit override would crash. `.env.example` updated to match (tracked).

### 6. How to recall
- STEP file: `docs/progress/STEP_018_qdrant_in_runner.md`
- Code: `finrag/vectordb/qdrant_backend.py::QdrantDenseIndex`, `ragas_runner.py::_build_dense_index`, `config.py::vectordb_backend`
- Exp: `docs/experiments/exp_022_hybrid_qdrant/`
- Proof: `results/smoke/exp_022_hybrid_qdrant_20260907_085855/` (untracked)

### 7. Next step (STEP_019)
Full exp_022 run (~50 min, live Qdrant required — keep `docker compose up`) → retrieved-set overlap vs exp_021 per-Q + metrics-within-noise verdict → leaderboard (no winner change expected; latency column only). If parity holds end-to-end, the serving story is told: hybrid+Qdrant is deployable as-is.
