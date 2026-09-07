# STEP_020 — FastAPI serving (product surface opens)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Sweep winner servable over HTTP with citations + cost; fully offline-tested. No ledger change.
- **Roadmap phase:** Week 11 Product (opens; system was deployable since STEP_019, now served)

### 1. Why
Benchmarks don't serve traffic. The product arc needs the frozen winner
(naive + hybrid + Flash) behind an API with health/cost/citations before
any demo, nightly job, or Streamlit UI can consume it.

### 2. What changed (files — this commit)
- `pyproject.toml` + `uv.lock` — NEW core deps `fastapi>=0.115`, `uvicorn>=0.30` (installed: fastapi 0.141.1, starlette 1.6.0).
- `api/__init__.py`, `api/main.py` — NEW service: `create_app(bundle?, generator?)`, lifespan builds corpus from eval filings when no bundle injected (import stays instant); GET /health (503 pre-build), POST /ask (pydantic 422s, 500s `from e`), GET /leaderboard passthrough. Same `retrieve_with_strategy` + `generate` as the runner — served answers match benchmarked behavior by construction.
- `finrag/retrieval.py` — `retrieve()` + `retrieve_with_strategy()` accept optional embedder (default: configured backend — frozen behavior). Runner bundles don't carry one, so all 7 ledger rows are unaffected.
- `tests/test_api.py` — NEW, 8 tests (health ok/503, ask citations/422s, leaderboard keys, full lifespan build from real filings with mocks, $0).
- `Makefile` — `serve` (hybrid over in-memory, zero-infra) + `serve-qdrant` (live store). sh-style `VAR=x` recipes match the file's existing WSL-first convention (`sleep`/`find`/`rm -rf` already sh-only).
- `docs/progress/STEP_020_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (7 rows), leaderboard, eval set, runner behavior.
- NOT committed: nothing ephemeral this step (no smoke/benchmark runs).

### 3. How it works
Tests inject bundle+MockGenerator (bundle may carry `"embedder"` — the
only new retrieval behavior, defaulting off). Production lifespan calls
`build_index_for_qa_pairs` with settings; `make serve` pins hybrid via
env. /ask validates (1–2000 chars, top_k 1–20), retrieves, generates,
returns citations with ticker/section + tokens/cost/latency.

### 4. How to verify
```bash
uv run pytest tests/test_api.py -q
make serve  # then: curl -X POST localhost:8000/ask -H 'Content-Type: application/json' -d '{"question":"What was Apple revenue in FY2023?"}'
```

### 5. Result / numbers
- Unit: 109 passed (8 new). Ruff: own B904s fixed (`from e`); rest pre-existing classes.
- Three honest test failures fixed en route, all recorded: (a) machine OS env exports `VECTORDB_BACKEND=chroma`, which BEATS the `.env` file in pydantic-settings — STEP_018's `.env` fix was necessary but insufficient; tests now pin the var via monkeypatch, `make serve` pins via recipe env. **User action: delete the machine-level `VECTORDB_BACKEND=chroma`** (Windows Environment Variables) — it's invalid under the new validation and will crash any run that doesn't override it. (b) 503 test ran lifespan by using `with` — fixed to no-lifespan client. (c) MockEmbedder hash space is not semantic — ranking assertions must use verbatim-text queries (cosine 1.0); worse, the /ask path embedded questions with the global Vertex backend against mock index vectors (cross-space garbage) — fixed by threading an optional embedder through `retrieve()` (runner bundles unaffected, default off).
- Live boot ($, slow) deliberately NOT run — lifespan-build test covers the production path offline.

### 6. How to recall
- STEP file: `docs/progress/STEP_020_fastapi_serving.md`
- Code: `api/main.py`; tests: `tests/test_api.py`; serve: `Makefile::serve`
- Deps: `pyproject.toml` (fastapi/uvicorn)

### 7. Next step (STEP_021 candidate)
Streamlit demo (`ui/`, needs streamlit dep + `make ui` exists but unimplemented) hitting this API; or rerank phase (exp_030); or Vertex Search pre-deploy. Recommend Streamlit next — smallest step to a clickable product on top of this API.
