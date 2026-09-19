# STEP_042 — readme_table.py generator (refresh-rot ends, 201 tests)

- **Date:** 2026-09-19
- **Git commit:** PENDING (this step)
- **Goal:** Never hand-edit the README results table again. `make readme-table` regenerates it from the ledger; `--check` fails stale.
- **Roadmap phase:** Polish (refresh-rot generator — filed twice, now built)

### 1. Why
Three manual README refreshes (STEP_036/038/041) each hand-copied 12–13 rows. Fourth refresh forced the generator, as predicted in STEP_041.

### 2. What changed (files — this commit)
- `scripts/readme_table.py` (new) — ledger → markdown table + `N benchmarked experiments, M tests` tagline. `EXP_META` maps exp_name → (label, retrieval); unknown exps raise `KeyError` (loud, not mislabeled). Bold = unique column maxima only (ties stay plain); label bold iff row uniquely leads ALL four columns (sweep leader, auto-transfers on dethrone). Test count is AST-derived incl. `@parametrize` multipliers — matches `pytest -q` collection exactly (201). `--check` exits 1 when stale (CI hook).
- `tests/test_readme_table.py` (new, 10 tests) — loud unknown-exp, bold/tie/None rendering, parametrize counting, idempotent rewrite, missing-marker error.
- `Makefile` — `readme-table` + `readme-table-check` targets (`.PHONY` updated).
- `README.md` — table wrapped in `<!-- RESULTS:START/END -->` markers; generator-verified FRESH; structure lines fixed (exp_001…044 + vectordb 050…052, STEP_001…042, `readme_table.py` listed, 201 tests).
- `docs/progress/STEP_042_*` (this file) + `PROGRESS.md` index update.
- NOT changed: code, ledger (13 rows), leaderboard, eval set.

### 3. How to verify
```bash
make readme-table-check  # FRESH (or: uv run python scripts/readme_table.py --check)
uv run pytest tests/test_readme_table.py -q  # 10 passed
```

### 4. Result
Full suite: 197 passed, 4 skipped (live Qdrant/Weaviate unreachable — docker down, same skips as designed). Ruff: new files clean; 75 pre-existing findings in `finrag/`+`tests/` untouched (out of scope, predate this step).

### 5. How to recall
- STEP file: `docs/progress/STEP_042_readme_generator.md`
- Generator: `scripts/readme_table.py`
- Rule for future experiments: append 2-line `EXP_META` entry, run `make readme-table`, commit.

### 6. Next step (STEP_043 candidate)
Roadmap Open row only: hybrid+multiquery/HyDE combos (low priority), multi-worker fleet, nightly cron activation, auto-router/semantic cache. All core phases DONE.
