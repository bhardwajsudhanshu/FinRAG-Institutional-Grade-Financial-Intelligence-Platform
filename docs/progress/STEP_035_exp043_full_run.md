# STEP_035 — exp_043 full run (139 Q): expansion is noise, retired

- **Date:** 2026-09-08 (10:35–12:00 UTC, 5084.8s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Gain-concentration verdict on question expansion; update every record.
- **Roadmap phase:** Retrieval leftovers (multi-query measured and retired)

### 1. Why
STEP_034 smoke went 6/6 (fourth ever). Only the full set plus paired
per-Q analysis can separate concentrated gains from uniform noise.

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 12 `exp_043_multi_query` (clean append, 4447 chunks).
- `results/exp_043_multi_query/per_question.jsonl` — NEW, 139 rows (all dense+multiquery).
- `results/leaderboard.json` — refreshed, NO winner change (correct); snapshot `leaderboard_20260908_120031.json`.
- `docs/experiments/exp_043_multi_query/analysis.md` — full analysis (McNemar verdict, BM25-overlap curiosity, retire decision).
- `docs/progress/STEP_035_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='dense'; $env:MULTIQUERY_ENABLED='true'; $env:RERANK_BACKEND='none'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_043_multi_query
uv run python tests/eval/update_leaderboard.py
```
(All five pinned — multiquery joins the pin list.) No kill, no rerun, no 429s. Concentration math via `uv run python -c` over canonical per-Q files (non-OOS slice for cross-era honesty).

### 4. Result / numbers
139 Q / 4447 chunks; cr=0.8003, fa=0.9199, ar=0.7317; hit@5=0.5755, cite=0.5252; content=0.7194, cite_content=0.6978; 25153ms/Q; $0.0378 (+~$0.01 expansion invisible in row). Non-OOS: 82 vs exp_001's 78 — net +4 with 9 gained / 5 lost (p≈0.42, not significant). Curiosity: content ties BM25's 0.7194 exactly with only 82/100 Q overlap (union would be 0.849 — oracle-only, filed as hybrid+multiquery hypothesis). Per-type: no concentration (section exactly exp_001's 0.689). Verdict: RETIRE on dense.

### 5. Evaluation/methods changes
1. **Ledger**: clean row-12 append. No migration.
2. **Leaderboard**: refreshed, no winner change (exp_030 sweeps all 5). Snapshot added (by design).
3. **Methods upgrade**: paired discordant-pair (McNemar) reasoning adopted as standard for same-set comparisons — headline deltas alone mislead (this verdict's core).

### 6. How to recall
- STEP file: `docs/progress/STEP_035_exp043_full_run.md`
- Row: `results/experiments.csv` line 13; per-Q: `results/exp_043_multi_query/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260908_120031.json`
- Exp: `docs/experiments/exp_043_multi_query/analysis.md`

### 7. Next step (STEP_036 candidate)
Serving hardening (workers/persistent collection), README refresh with closed phases, or hybrid+multiquery combo (low priority). Recommend README refresh: 12 rows, 5 closed phases, and the front page still shows the STEP_028-era table.
