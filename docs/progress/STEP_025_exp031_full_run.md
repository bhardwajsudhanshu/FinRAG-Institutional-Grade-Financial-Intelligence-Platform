# STEP_025 — exp_031 full run (139 Q): challenger loses, phase closed

- **Date:** 2026-09-07 (20:02–20:51 UTC, 2959.4s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Quality-within-noise verdict on MiniLM vs Flash; update every record.
- **Roadmap phase:** Rerank (CLOSED — Flash-or-off decision, MiniLM retired)

### 1. Why
STEP_024 proved MiniLM plumbing. ADR-006's challenger thesis needs the
full-set verdict: within noise of exp_030 (content 0.8849) at $0, or not.

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 9 `exp_031_minilm_rerank` (clean append, 4447 chunks).
- `results/exp_031_minilm_rerank/per_question.jsonl` — NEW, 139 rows (all hybrid+cross-encoder).
- `results/leaderboard.json` — refreshed, NO winner change (correct); snapshot `leaderboard_20260907_205125.json`.
- `docs/experiments/exp_031_minilm_rerank/analysis.md` — full analysis (verdict, per-type, latency ledger, retirement decision).
- `docs/progress/STEP_025_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:HF_HOME='F:/.hf-cache'; $env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='hybrid'; $env:RERANK_BACKEND='cross-encoder'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_031_minilm_rerank
uv run python tests/eval/update_leaderboard.py
```
No kill, no rerun, no 429s. Per-type + ledger math via `uv run python -c` over canonical files.

### 4. Result / numbers
139 Q / 4447 chunks; cr=0.8430, fa=0.8887, ar=0.7027; hit@5=0.6259, cite=0.5683; **content=0.7698 (BELOW hybrid 0.8129 — rerank hurts)**, cite_content=0.7554; 9442ms/Q (4.4× faster than Flash's 42s); row $0.0370, $0 scoring confirmed (no `rerank` ops in cost log). Per-type: lookup 0.701 (worst gap), section 0.800 (= hybrid), synthesis 0.667 (< hybrid 0.778), OOS 1.000/0.889. Verdict: ms-marco mis-orders 10-K language (distributional, not capacity) — leadership = Flash ($$) or OFF (free); MiniLM retired, strictly dominated.

### 5. Evaluation/methods changes
1. **Ledger**: clean row-9 append. No migration.
2. **Leaderboard**: refreshed, no winner change (exp_030 sweeps all 5). Snapshot added (by design).
3. **No methods changes.**

### 6. How to recall
- STEP file: `docs/progress/STEP_025_exp031_full_run.md`
- Row: `results/experiments.csv` line 10; per-Q: `results/exp_031_minilm_rerank/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260907_205125.json`
- Exp: `docs/experiments/exp_031_minilm_rerank/analysis.md`

### 7. Next step (STEP_026 candidate)
API "best answer" mode flag (serve reranked flagship vs cheap default) or nightly-drift job design or Vertex Search pre-deploy benchmark. Recommend best-answer flag: one small serving change that products the sweep.
