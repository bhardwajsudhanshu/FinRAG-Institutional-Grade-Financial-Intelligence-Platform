# STEP_038 — README + deploy refresh (serving profiles current)

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** Front door and deploy guide match the hardened serving story. No ledger change.
- **Roadmap phase:** Polish (second pass — STEP_028 wrote it, 10 steps landed since)

### 1. Why
STEP_028's docs predate persistent Qdrant, exp_041/042/043 verdicts,
and the 175→182 test growth. Stale deploy instructions are worse than
none (a reader following "index rebuilds per worker" would misplan
capacity that STEP_037 already fixed).

### 2. What changed (files — this commit)
- `README.md` — 3 new results rows (041/042/043 + verdicts), architecture options line, serve block gains persistent flow (`build_serve_index` once → `QDRANT_RECREATE=false` attach in ~2s) + best-answer flag, counts (182 tests, STEP_001…037), structure (already current), roadmap (serving hardening DONE, Vertex measured, leftovers closed).
- `docs/03_deploy.md` — pre-warm + attach checklist (replaces rebuild-per-worker advice), Vertex Search measured verdict, multi-instance status corrected (shared collection BUILT; upsert-on-ingest still filed).
- `docs/progress/STEP_038_*` (this file) + `PROGRESS.md` index update.
- NOT changed: code, ledger (12 rows), leaderboard, eval set. Docs-only (suite green from STEP_037; rerun at commit).

### 3. How to verify
```bash
git diff README.md docs/03_deploy.md  # figures vs results/experiments.csv locked rows
uv run pytest tests -q  # untouched code paths, still green
```

### 4. Result
Front door current through STEP_037. Filed (not built): `scripts/readme_table.py` generator (STEP_028 idea, still open — third manual refresh proves the need).

### 5. How to recall
- STEP file: `docs/progress/STEP_038_readme_deploy_refresh.md`
- Front door: `README.md`; ops: `docs/03_deploy.md`

### 6. Next step (STEP_039 candidate)
Hybrid+multiquery combo (low priority), HyDE (untested), or the readme_table.py generator (ends refresh-rot). Recommend HyDE: last retrieval family with no data at all.
