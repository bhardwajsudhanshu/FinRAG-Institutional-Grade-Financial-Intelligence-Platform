# STEP_016 — Vector-DB phase opens: ADR-005 + interface + Qdrant :memory:

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Make the vector store benchmarkable with quality frozen; prove Qdrant parity + latency offline. No ledger change.
- **Roadmap phase:** Vector-DB benchmark (opens; awaits Docker daemon for live runs)

### 1. Why
STEP_015 froze quality (hybrid sweeps). Remaining question is operational:
which store serves dense retrieval at production latency. ADR-005 (written
first) orders Qdrant → Weaviate → Vertex Search and locks parity-not-quality
methodology + exp numbers (050/051/052 — 030/040 were promised to rerank/RAPTOR).

### 2. What changed (files — this commit)
- `docs/decisions/adr_005_vectordb_benchmark.md` — NEW (order, parity methodology, gates, criteria).
- `finrag/vectordb/{__init__,base,qdrant_backend}.py` — NEW interface (`upsert/query/len/close`, lazy client import) + Qdrant impl (memory or URL, payloads for future filtered benchmarks).
- `scripts/benchmark_vectordb.py` — NEW harness (eval chunks + 139 Q texts, mock $0, JSON out; `--qdrant-url` switches memory→docker).
- `tests/test_vectordb.py` — NEW, 9 tests (`:memory:`, incl. parity semantics).
- `docs/experiments/exp_050_qdrant/{README,config.yaml,analysis.md}` — NEW scaffold with preview numbers.
- Env (not a file change): `uv sync --extra vectordbs` → qdrant-client 1.19.0 + weaviate-client 4.23.0 materialized into `.venv` (`uv.lock` unchanged — already locked, verified via clean `git status`).
- `docs/progress/STEP_016_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (6 rows), leaderboard, eval set, dense path.
- NOT committed: `results/benchmarks/qdrant_preview.json` (ephemeral instrument output, like smoke).

### 3. How it works
Backends store caller vectors, return ranked chunk_ids; `QdrantBackend`
defaults to `:memory:`. Harness embeds 4447 naive chunks once (mock),
upserts, times both stores per question, checks top-1 + set parity.

### 4. How to verify
```bash
uv run pytest tests/test_vectordb.py -q
EMBEDDER_BACKEND=mock uv run python scripts/benchmark_vectordb.py --out results/benchmarks/qdrant_preview.json
```

### 5. Result / numbers
- Unit: 9 passed. Two honest test failures fixed during the step, both recorded: (a) QdrantBackend didn't subclass the ABC (contract unenforced — now does); (b) exact-order parity is unachievable across float32/float64 + HNSW on near-tie tails → parity redefined as top-1 + set equality, which is also how hit@5 itself is scored (order-insensitive). Plus deprecated `recreate_collection` replaced.
- Preview (mock, :memory:, $0): upsert 4447 in 6.9s; p50 34.75ms / p95 41.78ms (**~39×** brute-force 1350/1633ms); parity **1.000/1.000** on all 139 Q's. Clears all three ADR-005 gates pending docker confirmation.
- Ruff: only E402 (shared sys.path pattern), pre-existing.
- Infra truth: Docker daemon DOWN (Desktop not started — user action needed for live runs); clients installed.

### 6. How to recall
- STEP file: `docs/progress/STEP_016_vectordb_interface_qdrant.md`
- Decision: `docs/decisions/adr_005_vectordb_benchmark.md`
- Code: `finrag/vectordb/`; harness: `scripts/benchmark_vectordb.py`; tests: `tests/test_vectordb.py`
- Exp: `docs/experiments/exp_050_qdrant/`; numbers: `results/benchmarks/qdrant_preview.json` (untracked)

### 7. Next step (STEP_017 candidate)
Docker Desktop up (user) → `docker compose up -d` → rerun harness with `--qdrant-url` (same script) → canonical exp_050 numbers + ledger row + Weaviate impl (needs live server; same interface). Vertex Search last (hourly billing — bench + teardown same-day).
