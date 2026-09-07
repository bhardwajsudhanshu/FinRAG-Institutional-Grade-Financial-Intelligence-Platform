# STEP_026 — API best-answer mode (sweep productized per-request)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Serve Flash-reranked flagship answers behind a per-request flag; cheap default untouched. No ledger change.
- **Roadmap phase:** Product (serving options complete: cheap default + best mode)

### 1. Why
exp_030 won quality at $0.171/42s-per-Q — nobody wants that as the only
mode, and nobody wants to leave it uns servable. Per-request flag gives
both: default hybrid (free, fast) + opt-in reranked flagship.

### 2. What changed (files — this commit)
- `api/main.py` — `AskRequest.rerank: bool = False`; `AskResponse.reranked: bool`; `create_app(..., reranker=None)` (tests inject; production lazily builds Flash pointwise on first `rerank=true`, needs GCP — fails as clean 500 otherwise); fetch widened to max(top_k, 10) only in best mode.
- `ui/streamlit_app.py` — `query_api(..., rerank=False)` (timeout floor 300s in best mode); "Best answer (Flash re-rank...)" checkbox + "· re-ranked" caption.
- `tests/test_api.py` — best-mode tests (default `reranked=false`; injected reversing reranker proves ordering flows to citations).
- `tests/test_ui.py` — rerank flag reaches the API payload (true + default-false).
- `docs/progress/STEP_026_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (9 rows), leaderboard, eval set, runner defaults. Live boot deliberately NOT run (lifespan-build test covers the path; a served reranked answer is proven by exp_030 rows + unit ordering).

### 3. How it works
`rerank=false` (default): identical path to STEP_020. `rerank=true`:
fetch 10 → injected-or-Flash rerank → top_k → generate; response marks
`reranked: true` and the UI captions it. Scoring calls bill to the normal
cost log (`rerank` op).

### 4. How to verify
```bash
uv run pytest tests/test_api.py tests/test_ui.py -q
# live: make serve & curl -X POST localhost:8000/ask -d '{"question":"...","rerank":true}'
```

### 5. Result / numbers
- Full suite: 143 passed + 3 skipped (Weaviate — Docker Desktop is down again as of this step; tests skip cleanly by design).
- Ruff: no new issues (shared E402 pattern only).
- Env notes (recorded, both user-side): (a) machine OS `VECTORDB_BACKEND=chroma` still present — delete it; (b) MiniLM live test used the C: HF cache (this shell lacked `HF_HOME`) — recommend machine-level `HF_HOME=F:/.hf-cache` (or per-command prefix as in exp_031 docs) to honor the F: discipline.

### 6. How to recall
- STEP file: `docs/progress/STEP_026_api_best_answer.md`
- Code: `api/main.py` (rerank branch), `ui/streamlit_app.py` (checkbox)
- Tests: `tests/test_api.py::TestBestAnswerMode`, `tests/test_ui.py::test_rerank_flag_reaches_api`

### 7. Next step (STEP_027 candidate)
Nightly-drift job design (cron + `make eval-nightly` + alert thresholds) or Vertex Search pre-deploy benchmark or README/deploy-guide polish. Recommend nightly job: it protects all 9 ledger rows going forward.
