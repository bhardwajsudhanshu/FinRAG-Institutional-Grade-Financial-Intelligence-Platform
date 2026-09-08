# STEP_040 — exp_044 full run (139 Q): suggestive, kept, not default

- **Date:** 2026-09-08 (15:35–16:49 UTC, 4392.3s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Vague-Q verdict on HyDE; update every record.
- **Roadmap phase:** Retrieval leftovers (HyDE measured — question-side closed)

### 1. Why
STEP_039 smoke went 6/6 (fifth ever). Only paired full-set analysis can
separate concentrated gains from noise — multiquery's lesson applied.

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 13 `exp_044_hyde` (clean append, 4447 chunks).
- `results/exp_044_hyde/per_question.jsonl` — NEW, 139 rows (all dense+hyde).
- `results/leaderboard.json` — refreshed, NO winner change (correct); snapshot `leaderboard_20260908_164912.json`.
- `docs/experiments/exp_044_hyde/analysis.md` — full analysis (McNemar verdict, curiosities, dense-side ordering).
- `docs/progress/STEP_040_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='dense'; $env:HYDE_ENABLED='true'; $env:RERANK_BACKEND='none'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_044_hyde
uv run python tests/eval/update_leaderboard.py
```
(All five pinned.) No kill, no rerun, no 429s. Paired math via `uv run python -c` over canonical per-Q files (non-OOS slice for cross-era honesty).

### 4. Result / numbers
139 Q / 4447 chunks; cr=0.8140 (noses past naive 0.8058 — only dense-side change that lifts recall), fa=0.9024, ar=0.7512; hit@5=0.5899, cite=0.5396; **content=0.7482**, cite_content=0.7194 (= BM25 exactly, third exact-tie); 20128ms/Q; $0.0377 (+139 HyDE writes ~$0.01 invisible in row). Non-OOS paired: 86 vs 78 — net +8 (13 gained / 5 lost, p≈0.10, suggestive). Per-type: no concentration (lookup 0.716 = BM25 exactly). Verdict: KEEP available (best dense-only: 0.748 > 0.719 > 0.698 > 0.604), not default; hybrid+HyDE filed low-priority.

### 5. Evaluation/methods changes
1. **Ledger**: clean row-13 append. No migration.
2. **Leaderboard**: refreshed, no winner change (exp_030 sweeps all 5). Snapshot added (by design).
3. **No methods changes.**

### 6. How to recall
- STEP file: `docs/progress/STEP_040_exp044_full_run.md`
- Row: `results/experiments.csv` line 14; per-Q: `results/exp_044_hyde/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260908_164912.json`
- Exp: `docs/experiments/exp_044_hyde/analysis.md`

### 7. Next step (STEP_041 candidate)
Serving hardening follow-ups (workers, upsert-on-ingest), hybrid+HyDE or hybrid+multiquery combos (both low priority), or README refresh with all closed phases. Recommend README refresh: front door is 5 steps stale and everything since is verdicts, not code.
