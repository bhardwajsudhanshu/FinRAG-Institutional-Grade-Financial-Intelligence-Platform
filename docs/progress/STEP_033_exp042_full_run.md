# STEP_033 — exp_042 full run (139 Q): exact tie, hierarchy retires

- **Date:** 2026-09-08 (09:08–10:04 UTC, 3367.8s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Both-bars verdict on the combo; update every record.
- **Roadmap phase:** Retrieval leftovers (hierarchy CLOSED — retired, not redeemed)

### 1. Why
STEP_032 smoke went 6/6 (second ever). Only a full run can grade both
single-variable bars (>0.6978 AND >0.8129).

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 11 `exp_042_hybrid_parent` (clean append, 4447 parents).
- `results/exp_042_hybrid_parent/per_question.jsonl` — NEW, 139 rows (all hybrid-parent).
- `results/leaderboard.json` — refreshed, NO winner change (correct); snapshot `leaderboard_20260908_100445.json`.
- `docs/experiments/exp_042_hybrid_parent/analysis.md` — full analysis (tie verdict, per-type, retirement decision).
- `docs/progress/STEP_033_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='hybrid-parent'; $env:RERANK_BACKEND='none'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_042_hybrid_parent
uv run python tests/eval/update_leaderboard.py
```
(All four pinned.) No kill, no rerun. One RAGAS-retry 429 (auto). Per-type math via `uv run python -c` over the canonical per-Q file.

### 4. Result / numbers
139 Q / 4447 parents / ~13.2K children; cr=0.8223, fa=0.9190, ar=0.7245; hit@5=**0.6835 (best chunk_id)**, cite=**0.6187 (best chunk_id)**; **content=0.8129 — EXACT tie with exp_021 (113/139 both)**; cite_content=0.7842; 10563ms/Q; $0.0366. Per-type: lookup 0.791 (best slice anywhere), section 0.778 (+13pp vs exp_041), synthesis 0.778 (+22pp vs exp_041), OOS 1.000/0.778. Bars: vs exp_041 CLEARED (+11.5pp), vs exp_021 TIED — partial redemption (fuses cleanly, no interference) but no serving case at 3× cost.

### 5. Evaluation/methods changes
1. **Ledger**: clean row-11 append. No migration.
2. **Leaderboard**: refreshed, no winner change (exp_030 sweeps all 5). Snapshot added (by design).
3. **No methods changes.** Methodology note: three 6/6 smokes → 0.698/0.813/0.813 at scale. Smoke is plumbing proof, never signal (now a triply-confirmed rule).

### 6. How to recall
- STEP file: `docs/progress/STEP_033_exp042_full_run.md`
- Row: `results/experiments.csv` line 12; per-Q: `results/exp_042_hybrid_parent/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260908_100445.json`
- Exp: `docs/experiments/exp_042_hybrid_parent/analysis.md`

### 7. Next step (STEP_034 candidate)
Multi-query/HyDE (question-side, last untested retrieval family) or serving hardening (workers/persistent collection) or README refresh with closed phases. Recommend multi-query: cheapest remaining experiment with a clean ablation (3 paraphrases + RRF vs single query).
