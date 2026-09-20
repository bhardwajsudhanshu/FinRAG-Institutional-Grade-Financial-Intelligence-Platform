# STEP_043 — 2-worker fleet verified live (multi-worker fleet: done)

- **Date:** 2026-09-20
- **Git commit:** PENDING (this step)
- **Goal:** Prove `uvicorn --workers 2` serves cited Flash answers off persistent Qdrant with zero rebuilds. No ledger change.
- **Roadmap phase:** Open row → multi-worker fleet (now DONE; 3 Open items left)

### 1. Why
STEP_037 named multi-worker uvicorn as the reason for attach-if-populated, but no fleet ever booted. Docker up + Vertex key fixed (see §5) made this the right step.

### 2. What changed (files — this commit)
- `Makefile` — `serve-fleet` target (2 workers, attach mode) + `.PHONY`.
- `README.md` — Product row notes fleet verified; Open row drops multi-worker fleet.
- `docs/progress/STEP_043_*` (this file) + `PROGRESS.md` index update.
- NOT changed: code, ledger (13 rows), leaderboard, eval set, `.env`/`secrets/` (local-only, never committed).

### 3. How to verify
```bash
make serve-fleet  # then: curl /health + 2 concurrent POST /ask
uv run pytest tests/test_vectordb.py -q  # 20/20 live
```

### 4. Result
- Boot: both workers attached independently to `finrag_eval` (4447 pts, no re-embed), server ready ~44s after start (mostly corpus parse + BM25 build, not embedding).
- 2 concurrent `/ask` → 200 with real cited Flash answers: Apple FY2023 revenue $383,285M ($0.00031, 6.4s) + risk-factors synthesis ($0.00029, 15.8s). Total proof cost ≈ $0.0006.
- Full suite earlier this step (docker up): 201 passed, 0 skipped. Vectordb live re-run post-restart: 20/20.

### 5. How to recall (auth + ops lessons, read before next serve step)
- Vertex 401s were TWO stacked issues: (a) `.env` pointed at the deleted `vertex-key.json` — updated to `secrets/kaggle-submission2-509111-04eddcc1238f.json`; (b) key issued for project `kaggle-submission2-509111` but `GCP_PROJECT_ID=kaggle-submission2` — updated. `make vertex-check` passes (live dim-768 ping).
- Parent shell carries STALE process-scope env (`GOOGLE_APPLICATION_CREDENTIALS`→deleted file, `GCP_PROJECT_ID`→old project, backends→vertex) that beats `.env`. Override in-session when running under this agent; normal shells use `.env` (now correct).
- Fleet-2/3 401 post-mortem: killing the uvicorn parent ORPHANS workers holding :8000 — subsequent boots die on bind while health checks hit the orphan. Always verify `Get-Process uvicorn` / port free after stop; `serve-fleet` comment says "kill the whole tree".
- Docker Desktop was down mid-step (pipe missing); relaunching restored all 4 containers with volumes intact (4447 pts survived).

### 6. Next step (STEP_044 candidate)
Remaining Open row: hybrid+multiquery/HyDE combos (low priority, ~$ Vertex), nightly cron activation, auto-router/semantic cache. Recommend nightly cron activation (free, ops-shaped, pairs with the drift guard).
