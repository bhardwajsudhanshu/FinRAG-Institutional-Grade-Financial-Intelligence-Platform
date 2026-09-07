# STEP_013 — exp_020 full run (139 Q) + ledger updates

- **Date:** 2026-09-07 (05:36–06:07 UTC, 1827.1s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Score the BM25 ablation; update every record the run changed.
- **Roadmap phase:** Week 5-8 Retrieval (1/2 Phase-3 runs done)

### 1. Why
STEP_012 proved BM25 plumbing (6 Q). ADR-004's lookup-vs-section bet and
the WMT/AMZN prediction need the full-set numbers before hybrid can be
judged (hybrid must beat *both* sides).

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 5 `exp_020_bm25` (clean append, 4447 chunks = exp_001 count).
- `results/exp_020_bm25/per_question.jsonl` — NEW, 139 rows (all `retrieval_strategy=bm25`).
- `results/leaderboard.json` — `chunking_content` → exp_020 (0.7194); `retrieval` stays exp_001; `last_updated` 2026-09-07T06:07:03.
- `results/leaderboard_snapshots/leaderboard_20260907_060703.json` — NEW.
- `docs/experiments/exp_020_bm25/analysis.md` — full analysis (hit-vs-recall split, ADR-004 grading, robustness note, hybrid bar).
- `docs/progress/STEP_013_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='bm25'; uv run python -m finrag.cli.eval --exp exp_020_bm25
uv run python tests/eval/update_leaderboard.py
```
Index 58s all filings. One new failure mode: q_0053 Flash returned 2 identical parts → SDK `.text` raised → runner's except caught it (empty answer, 1/139). Proposed STEP_014 micro-fix (join parts), recorded in analysis.

### 4. Result / numbers
139 Q / 20 filings / 4447 chunks; cr=0.7238 (lowest), fa=0.8604, ar=0.6670 (lowest); hit@5=0.6115 (best chunk_id), cite=0.5396; **hit@5_content=0.7194 (best), cite_content=0.7050 (best)**; 4374ms/Q (fastest); $0.0354. Lookup 0.716 ✓ / section 0.578 ✓ per ADR-004; synthesis **0.889 unpredicted** (rare-term anchors); WMT 0.250→0.625 ✓; AMZN stuck 0.333. Hybrid bar: beat 0.7194 hit AND 0.8058 recall together.

### 5. Evaluation/methods changes
1. **Ledger**: clean row-5 append. No migration.
2. **Leaderboard**: `chunking_content` exp_004→exp_020 (note: a retrieval exp leads a `chunking_*` category — category tracks the metric, rename deferred to a future locked schema rev).
3. **No methods changes.** Watch item: first SDK multi-part failure → STEP_014 fix candidate.

### 6. How to recall
- STEP file: `docs/progress/STEP_013_exp020_full_run.md`
- Row: `results/experiments.csv` line 6; per-Q: `results/exp_020_bm25/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260907_060703.json`
- Exp: `docs/experiments/exp_020_bm25/analysis.md`

### 7. Next step (STEP_014 candidate)
1. Micro-fix: join multi-part texts in `VertexGenerator.generate` (+ unit test with stubbed response) — 5-minute change, no re-run needed (affects 1/139 Q).
2. Then exp_021 hybrid scaffold + smoke (code already in STEP_012), full run after.
