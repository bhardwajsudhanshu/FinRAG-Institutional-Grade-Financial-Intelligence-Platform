# STEP_041 — README refresh (13 rows, HyDE kept, 191 tests)

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** Front door current through STEP_040. No ledger change.
- **Roadmap phase:** Polish (third pass — refresh-rot continues, generator still filed-not-built)

### 1. Why
STEP_038's README predates exp_044 (HyDE verdict), the 175→191 test growth,
and three closed steps. Also noted while editing: the table through
exp_043 was already current — the user keeps it updated between steps
(observed STEP_036 area). This pass adds exp_044 + serving-adjacent deltas.

### 2. What changed (files — this commit)
- `README.md` — exp_044 row (0.8140/0.9024/0.7482/0.5396) + HyDE verdict in headlines + architecture options line (HyDE kept) + counts (13 exps, 191 tests, STEP_001…040) + structure (`hyde.py`) + roadmap (HyDE kept-not-default, Open row current).
- `docs/progress/STEP_041_*` (this file) + `PROGRESS.md` index update.
- NOT changed: code, ledger (13 rows), leaderboard, eval set. Docs-only (suite green from STEP_039; rerun at commit).

### 3. How to verify
```bash
git diff README.md  # figures vs results/experiments.csv locked rows
```

### 4. Result
Front door current through STEP_040. Refresh-rot generator (`scripts/readme_table.py`) filed twice now, still unbuilt — fourth manual refresh will force it.

### 5. How to recall
- STEP file: `docs/progress/STEP_041_readme_refresh.md`
- Front door: `README.md`

### 6. Next step (STEP_042 candidate)
Serving hardening follow-ups (workers, upsert-on-ingest), hybrid+multiquery/HyDE combos (low priority), or the readme_table.py generator (build it before the fourth refresh). Recommend the generator: it ends this recurring chore.
