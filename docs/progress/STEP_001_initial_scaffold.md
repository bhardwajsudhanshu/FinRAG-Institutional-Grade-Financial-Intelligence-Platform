# STEP_001 — Initial scaffold

- **Date:** 2026-09-05
- **Git commit:** `6cc10d3` Initial commit: Starting this project
- **Goal:** Runnable repo skeleton with mock pipeline end-to-end.
- **Roadmap phase:** Week 1-2 Foundation (start)

### 1. Why
Need a runnable baseline before any real SEC data or Vertex calls. Mock backends let `make ingest-sample` + `make query` work offline.

### 2. What changed (files)
- `pyproject.toml` — deps (pydantic, chromadb, rank-bm25, typer, tenacity, loguru) + uv cache on F:.
- `finrag/config.py` — `Settings` from `.env` (backends, chunk sizes, top_k, paths).
- `finrag/chunking.py` — `naive_chunk_text` (512/50 tiktoken) + `chunk_sections`.
- `finrag/embeddings.py` — `MockEmbedder` (hash, L2-norm) + `VertexEmbedder` stub.
- `finrag/retrieval.py` — `InMemoryIndex` brute-force cosine.
- `finrag/generation.py` — `MockGenerator` templated + `VertexGenerator` stub, shared `SYSTEM_PROMPT`.
- `finrag/cost.py` — `record_call` + pricing table → `data/runtime_costs.jsonl`.
- `finrag/data/ingest_sec.py` + `parse_sections.py` — EDGAR fetch + Item 1/1A/7/7A/8 regex parser.
- `finrag/cli/ingest.py`, `ask.py`, `eval.py` — Typer CLIs.
- `docker-compose.yml` — Qdrant/Weaviate/Redis/Postgres (not yet used).
- `docs/00_overview.md`, `01_setup.md`, `decisions/adr_001_topic_choice.md`, `adr_002_google_stack.md` — the "why SEC + why Vertex" story.
- `docs/experiments/exp_001_naive_baseline/{README,config.yaml,results.json}` — skeleton (results.json = `not_run`).
- `Makefile`, `.env.example`, `README.md` — `make env / ingest-sample / query`.

### 3. How it works
- `ask.py:37-67` — ensure sample → parse → `chunk_sections` → `build_index` → `retrieve` → `generate`.
- Chunk ID shape `TICKER_DATE_section::idx` is the join key for all later evals.
- Cost log is append-only JSONL; mocks log 0.0 cost but real latency/tokens.

### 4. How to verify
```bash
make env
cp .env.example .env
make ingest-sample
make query Q="What are Apple's main risk factors?"
```

### 5. Result
Smoke test passes offline. No real metrics yet (exp_001 `results.json` = `not_run`).

### 6. How to recall
- Commit: `git show 6cc10d3 --stat`
- Docs: `docs/00_overview.md`, `docs/decisions/adr_001_topic_choice.md`, `adr_002_google_stack.md`

### 7. Next step
STEP_002 wires real Vertex AI so mocks can be swapped for Gemini + text-embedding-005.
