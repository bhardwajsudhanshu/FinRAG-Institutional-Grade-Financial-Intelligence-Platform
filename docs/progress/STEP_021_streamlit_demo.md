# STEP_021 — Streamlit demo on the API (clickable product)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Human-usable demo hitting the served sweep winner. No ledger change.
- **Roadmap phase:** Week 11-12 Product (demo live; polish remains)

### 1. Why
API without a face gets no users. The demo closes the loop eval →
serve → click: analyst types a question, sees a cited answer plus the
experiment leaderboard that produced the pipeline behind it.

### 2. What changed (files — this commit)
- `pyproject.toml` + `uv.lock` — NEW dep `streamlit>=1.38` (installed 1.63.0 + altair/pydeck/itsdangerous/narwhals/watchdog).
- `ui/__init__.py`, `ui/streamlit_app.py` — NEW dashboard: question input, top_k slider, answer + citations table + tokens/cost caption, sidebar backend health + leaderboard. Talks to the API over HTTP (`FINRAG_API_URL`, default localhost:8000) — exercises the REAL served path, not a copy of it. UI code in `main()` (runs only under `streamlit run`); helpers importable/testable.
- `tests/test_ui.py` — NEW, 10 tests (URL default/override, ask happy/connection/422/500 paths, health up/down, leaderboard flatten/empty). httpx stubbed — $0, no server.
- `docs/progress/STEP_021_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (7 rows), leaderboard, API, eval set. `Makefile::ui` already existed — no Makefile change needed.
- NOT committed: nothing ephemeral this step.

### 3. How it works
Two terminals: `make serve` (API :8000) + `make ui` (dashboard :8501).
Helpers: `api_url()` (env override, slash-stripped), `query_api()`
(human RuntimeErrors for connect/timeout/422/5xx), `fetch_health()` (None
when down, never raises), `fetch_leaderboard_winners()` (flattened
(category, winner, value), [] when down).

### 4. How to verify
```bash
uv run pytest tests/test_ui.py -q
uv run python -c "import ui.streamlit_app as m; print(m.api_url())"
make serve & make ui  # manual click-through (not run here — needs a browser)
```

### 5. Result / numbers
- Unit: 119 passed (10 new). Ruff: own RUF001 en-dashes fixed to hyphens; remaining E402 is the shared sys.path pattern.
- One invalid test written then fixed, recorded: `test_500 Surfaces_body` (space in name — caught at first run, never committed).
- Live click-through deliberately NOT run (no browser here) — helpers + import verified; manual QA is a user step.

### 6. How to recall
- STEP file: `docs/progress/STEP_021_streamlit_demo.md`
- Code: `ui/streamlit_app.py`; tests: `tests/test_ui.py`
- Run: `make serve` + `make ui`; remote API: `FINRAG_API_URL=http://host:8000 make ui`
- Deps: `pyproject.toml` (streamlit)

### 7. Next step (STEP_022 candidate)
Rerank phase (exp_030 cross-encoder — closes the context_recall↔citation gap from exp_001 analysis) or Vertex Search pre-deploy benchmark or nightly RAGAS drift job. Recommend rerank: cheapest remaining quality lever with a clean ablation (re-rank top-20 → top-5 vs raw top-5).
