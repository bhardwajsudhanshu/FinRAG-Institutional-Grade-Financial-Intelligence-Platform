# STEP_017 — Live docker benchmarks: Qdrant canonical + Weaviate impl

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Prove both benchmark paths against live servers; lock the production store decision. No RAG ledger change (ops benchmark).
- **Roadmap phase:** Vector-DB benchmark (Qdrant + Weaviate done live; Vertex Search deferred)

### 1. Why
STEP_016 proved `:memory:` parity/latency offline, but production runs in
docker and Weaviate had no implementation at all. ADR-005 gates need live
numbers on both before the store decision.

### 2. What changed (files — this commit)
- `docker-compose.yml` — THREE infra fixes: (a) `ENABLE_MODULES: ""` + `DEFAULT_VECTORIZER_MODULE: none` (transformers module with no endpoint crashed Weaviate at boot — fatal); (b) image 1.25.5 → 1.27.7 (client 4.23 refuses < 1.27.0); (c) added `50051:50051` (v4 client needs gRPC). Plus one poisoned-raft volume wipe + one version-skew wipe (both data-free, recorded in exp_051 analysis).
- `finrag/vectordb/weaviate_backend.py` — NEW `WeaviateBackend` (BYO vectors, batched upsert ≤500/batch — single 4447 insert exceeds the 10MB gRPC cap; `1-distance` scoring). `vector_config=self_provided` (non-deprecated API).
- `finrag/vectordb/__init__.py` — export it.
- `tests/test_vectordb.py` — 3 live Weaviate tests (skip cleanly without server).
- `scripts/benchmark_vectordb.py` — `--backend {qdrant,weaviate}`, `store` result block, try/finally close, noqa cleanup.
- `docs/experiments/exp_050_qdrant/analysis.md` — canonical docker section (p95 30.46ms, parity 1.0; preview-correction note included).
- `docs/experiments/exp_051_weaviate/{README,config.yaml,analysis.md}` — NEW with live numbers + verdict.
- `docs/progress/STEP_017_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (6 rows — ops benchmarks don't take RAG rows, recorded decision), leaderboard (vectordb stays null until a locked schema rev), eval set, dense path.
- NOT committed: `results/benchmarks/*.json` (3 ephemeral instrument outputs), `results/smoke/*` (user snapshots separately).

### 3. How it works
Same harness, same 4447 vectors, same 139 Q texts for both stores; mock embeddings ($0). Qdrant via `QdrantBackend(location=url)`; Weaviate via batched upsert + near_vector.

### 4. How to verify
```bash
make docker-up
uv run pytest tests/test_vectordb.py -q   # 12 pass live (skips cleanly without server)
EMBEDDER_BACKEND=mock uv run python scripts/benchmark_vectordb.py --qdrant-url http://localhost:6333 --collection <name> --out <path>
EMBEDDER_BACKEND=mock uv run python scripts/benchmark_vectordb.py --backend weaviate --collection <name> --out <path>
```

### 5. Result / numbers
- Tests: 12/12 live (9 Qdrant + 3 Weaviate). Ruff: only shared E402 pattern.
- Qdrant docker: p50 11.74 / **p95 30.46ms**, parity **1.0/1.0** → PASSES all gates. (Faster than `:memory:` 41.78 — preview-correction recorded.)
- Weaviate docker: p50 5.69 / **p95 9.71ms** (~3× Qdrant) BUT parity **0.9496/0.9468** → FAILS locked ≥0.99 gates (default-ef ANN approximation). Follow-up: ef tuning could re-open it.
- **Decision: production dense store = Qdrant** (exact, 30ms p95, $0 marginal). `make docker-up` verified from scratch.
- Client/server skew noted (client 1.19.0 vs server 1.10.0 warns, works).

### 6. How to recall
- STEP file: `docs/progress/STEP_017_live_docker_benchmarks.md`
- Exp records: `docs/experiments/exp_050_qdrant/analysis.md`, `docs/experiments/exp_051_weaviate/`
- Numbers: `results/benchmarks/{qdrant_preview,qdrant_docker,weaviate_docker}.json` (untracked)
- Infra: `docker-compose.yml` (3 fixes annotated inline)

### 7. Next step (STEP_018 candidate)
(a) Optional Weaviate ef-tuning rematch (same harness, one param); (b) Vertex AI Vector Search benchmark (GCP index deploy → bench → SAME-DAY teardown, ~$0.10/hr exposure); (c) then re-rank phase (exp_030) or FastAPI serving with the Qdrant-backed hybrid path. Recommend (c)-shaped STEP_018: wire Qdrant into the eval runner behind `vectordb_backend` for a parity end-to-end (quality reconfirmation on hybrid+Qdrant), deferring Vertex Search until pre-deploy.
