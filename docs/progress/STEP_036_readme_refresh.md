# STEP_036 — README refresh (front door tells the truth again)

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** README matches the 12-row ledger, 175 tests, and closed phases. No ledger change.
- **Roadmap phase:** Polish (second pass — STEP_028 wrote it, 8 experiments landed since)

### 1. Why
STEP_028's README described 9 experiments and 160 tests. Since then:
exp_041/042/043 measured, hierarchy retired twice, expansion retired,
Vertex Search measured-and-rejected, 15 more tests, 3 more phases closed.
A stale front door misleads faster than no front door.

### 2. What changed (files — this commit)
- `README.md` — results table 9→12 rows (all locked numbers), tagline counts, architecture options line, quickstart test count, structure (parentdoc/multiquery modules, exp_001…043, STEP_001…035, vertex-search harness), roadmap table (retrieval leftovers closed, vector DBs complete incl. Vertex verdict), PROGRESS pointer.
- `docs/progress/STEP_036_*` (this file) + `PROGRESS.md` index update.
- NOT changed: code, ledger (12 rows), leaderboard, eval set.
- Verification: every table figure re-checked against `results/experiments.csv` locked rows during writing (no new measurement — packaging only).

### 3. How to verify
```bash
git diff README.md  # spot-check 3-4 figures against results/experiments.csv
```

### 4. Result
Front door current through STEP_035. Next refresh due when the ledger grows (STEP_039+?) — or automate the table from CSV (filed, not built: a `scripts/readme_table.py` generator would end refresh-rot forever).

### 5. How to recall
- STEP file: `docs/progress/STEP_036_readme_refresh.md`
- Front door: `README.md`

### 6. Next step (STEP_037 candidate)
Serving hardening (workers/persistent collection from deploy notes), hybrid+multiquery combo (low priority), or HyDE (untested). Recommend hardening: production-shaped work that compounds (persistent collection also unblocks multi-instance + nightly cost cuts).
