# STEP_047 — Hybrid combos measured (both retire; roadmap complete)

- **Date:** 2026-09-20
- **Git commit:** PENDING (this step)
- **Goal:** Close the last Open item with two full 139-Q combo runs. No code change.
- **Roadmap phase:** Open row → hybrid combos (both measured-negative). Roadmap now EMPTY.

### 1. Why
The final filed idea: expansion/HyDE helped-or-tied on dense — do they stack on hybrid? Two one-variable runs vs exp_021, McNemar-paired, same frozen set.

### 2. What changed (files — this commit)
- `results/experiments.csv` — rows 14–15 (clean appends, 4447 chunks each).
- `results/exp_045_hybrid_multiquery/` + `results/exp_046_hybrid_hyde/` — per-Q JSONLs, 139/139.
- `results/leaderboard.json` + snapshot `leaderboard_20260920_165344.json` — refreshed, winners unchanged (exp_030 sweeps).
- `docs/experiments/exp_045_hybrid_multiquery/` + `exp_046_hybrid_hyde/` — config.yaml, README, analysis.md.
- `scripts/readme_table.py` — 2-line EXP_META additions (the STEP_042 rule working: loud KeyError → 2 lines → 15-row FRESH).
- `README.md` — generator-refreshed (15 rows) + Open row retired (roadmap complete).
- `docs/progress/STEP_047_*` (this file) + `PROGRESS.md` index update.
- NOT committed (per convention, snapshot later): `results/smoke/exp_045_combo_smoke_*`, `exp_046_combo_smoke_*`.
- NOT changed: code, eval set, thresholds.

### 3. How it works (the runs)
```bash
# smoke 6/6 each first ($0.0016), then full runs backgrounded (~80 min, ~$0.037 each)
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid MULTIQUERY_ENABLED=true RERANK_BACKEND=none VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_045_hybrid_multiquery
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid HYDE_ENABLED=true RERANK_BACKEND=none VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_046_hybrid_hyde
uv run python tests/eval/update_leaderboard.py
```
(Pinned all five + fresh GCP creds/project in-session; parent shell env still stale — see STEP_043 §5.)

### 4. Result
- **exp_045 hybrid+multiquery** (4969s, $0.0375): content 0.7842 vs 0.8129. Paired non-OOS: +1/−5, net −4, p~0.22. Expansion is noise-minus on hybrid (hybrid's BM25 side already covers the lexical variation). RETIRED everywhere.
- **exp_046 hybrid+HyDE** (4808s, $0.0368): content 0.8058 vs 0.8129. Paired: +5/−6, net −1, p~1.0 — a $0.01 wash (HyDE helped dense because dense had headroom; hybrid has none). One RAGAS-judge TimeoutError mid-run, retried, row complete. RETIRED as combo; HyDE stays kept-not-default (dense-only).
- Curiosity: `q_0065` gained by BOTH combos; `q_0032`/`q_0120` lost in both — the perturbations overlap, they don't complement.
- Question-side program CLOSED: multiquery noise twice, HyDE wash on hybrid. Total step spend ≈ $0.075.

### 5. How to recall
- STEP file: `docs/progress/STEP_047_hybrid_combos.md`
- Rows: `results/experiments.csv` lines 15–16; analyses in `docs/experiments/exp_04[56]_*/analysis.md`

### 6. Next step
None filed. The roadmap is empty and the ledger is frozen at 15 unless a new idea earns a run. Project complete — declare it.
