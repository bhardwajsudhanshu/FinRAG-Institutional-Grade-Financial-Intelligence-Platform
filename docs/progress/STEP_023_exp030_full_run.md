# STEP_023 — exp_030 full run (139 Q): gap closed, 5/5 sweep

- **Date:** 2026-09-07 (10:58–13:02 UTC, 7384.5s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** ADR-006's falsifiable gap bet on the full set; update every record.
- **Roadmap phase:** Rerank (Phase-5 quality COMPLETE — cost/latency now the question)

### 1. Why
STEP_022 proved rerank plumbing (6 Q). The gap verdict needs full-set
numbers: do citations rise toward recall with recall intact?

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 8 `exp_030_flash_rerank` (clean append, 4447 chunks).
- `results/exp_030_flash_rerank/per_question.jsonl` — NEW, 139 rows (all hybrid+flash-pointwise).
- `results/leaderboard.json` — SWEEP 5/5 decided (exp_030 everywhere); snapshot `leaderboard_20260907_130201_1.json` (same-second suffix — counter logic worked).
- `tests/eval/update_leaderboard.py` — `reranker` category metric `hit_at_10` (never scored a row) → `citation_accuracy` (locked column, fair: all rerank rows use naive chunks). ADR-006's promise, kept.
- `tests/eval/test_leaderboard.py` — reranker-category test (winner + runner-up + metric name).
- `docs/experiments/exp_030_flash_rerank/analysis.md` — full analysis (gap verdict RANKING, per-type, $0.171 all-in accounting, 4 lessons, rerank-ON-for-leadership decision).
- `docs/progress/STEP_023_*` (this file) + `PROGRESS.md` index update.
- No runner/chunker/retrieval/eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid RERANK_BACKEND=flash-pointwise VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_030_flash_rerank
uv run python tests/eval/update_leaderboard.py
```
(All four pinned — machine-OS chroma trap.) No kill, no rerun, no 429s, no multi-part errors. Per-type + true-cost accounting via `uv run python -c` over the canonical per-Q file and `data/runtime_costs.jsonl` (UTC stamps — machine runs +0530, filter accordingly).

### 4. Result / numbers
139 Q / 4447 chunks; cr=**0.9132**, fa=**0.9574**, ar=**0.7864**; hit@5=**0.7770** (+10.1pp), cite=**0.7266** (+11.5pp); content **0.8849** (+7.2pp), cite_content **0.8561** (+5.8pp); 41966ms/Q; row $0.0380, **true all-in $0.1714** (rerank $0.0712/1390 calls + gen $0.038 + embed $0.0622 — future cost math uses all-in). Per-type: lookup 0.866, section **0.889** (biggest win), synthesis flat 0.778 (needs coverage, not order — points at parent-doc/multi-query), OOS cite 0.778 (4 answered — only regression, small). Gap verdict: RANKING confirmed (citations rose AND recall rose).

### 5. Evaluation/methods changes
1. **Ledger**: clean row-8 append. No migration.
2. **Leaderboard**: 5/5 sweep (first ever — only `vectordb` null, by ops-design). `reranker` category defined (`citation_accuracy`), placeholder retired. Rolling overwrite + suffixed snapshot (by design).
3. **No methods changes** beyond the category definition. Watch: RAGAS ±1pp wobble stands (exp_022 lesson holds).

### 6. How to recall
- STEP file: `docs/progress/STEP_023_exp030_full_run.md`
- Row: `results/experiments.csv` line 9; per-Q: `results/exp_030_flash_rerank/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260907_130201_1.json`
- Exp: `docs/experiments/exp_030_flash_rerank/analysis.md`

### 7. Next step (STEP_024 candidate)
exp_031 MiniLM cross-encoder (cheap leadership?) or FastAPI "best answer" mode flag for rerank or nightly-drift job design. Recommend exp_031: it decides whether the sweep gets affordable.
