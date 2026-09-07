# STEP_019 — exp_022 full run: parity proven end-to-end

- **Date:** 2026-09-07 (09:16–10:05 UTC, 2563.8s; attempt 1 died in 5 min, attempt 2 clean)
- **Git commit:** PENDING (this step)
- **Goal:** Prove hybrid+Qdrant == hybrid+brute-force on the full set; update every record.
- **Roadmap phase:** Vector-DB benchmark (runner parity COMPLETE — serving story told)

### 1. Why
STEP_017 proved store parity on an isolated harness; STEP_018 wired the
store into the pipeline. Only a full run with per-Q set comparison closes
the loop to "deployable as-is".

### 2. What changed (files — this commit)
- `finrag/vectordb/qdrant_backend.py` — batched `upsert` (500/batch; single 4447 PUT = 72MB > 32MB cap → 400 killed attempt 1).
- `tests/test_vectordb.py` — batched-upsert regression test (120 pts, batch_size=7; assertion is membership not top-1 — hash-tie honesty).
- `results/experiments.csv` — row 7 `exp_022_hybrid_qdrant` (clean append).
- `results/exp_022_hybrid_qdrant/per_question.jsonl` — NEW, 139 rows.
- `results/leaderboard.json` — refreshed, NO winner change (correct); snapshot `leaderboard_20260907_100551.json`.
- `docs/experiments/exp_022_hybrid_qdrant/analysis.md` — full analysis (parity proof, latency dividend, 429 note, smoke-lesson).
- `docs/progress/STEP_019_*` (this file) + `PROGRESS.md` index update.
- No schema / eval-set / retrieval-math changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the runs)
```bash
$env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='hybrid'; $env:VECTORDB_BACKEND='qdrant'; uv run python -m finrag.cli.eval --exp exp_022_hybrid_qdrant
uv run python tests/eval/update_leaderboard.py
```
Attempt 1: 400 at upsert (payload cap). Fixed + tested, attempt 2 clean. Overlap check:
```bash
uv run python -c "...compare retrieved_chunk_ids exp_021 vs exp_022 per Q..."
# n=139 identical_order=139 identical_sets=139 mean_overlap=1.0
```

### 4. Result / numbers
139 Q / 4447 chunks; custom metrics IDENTICAL to exp_021 to 4 decimals (hit@5 0.6763, cite 0.6115, content 0.8129/0.7986; per-type identical); RAGAS within judge noise (cr 0.8760, fa 0.8979, ar 0.7587); **139/139 identical retrieved sets in identical order**; latency 7824ms (-1.1s/Q vs exp_021); $0.0365. One 429 (q_0069, caught) + one RAGAS-retry 429 (auto) — 429s now routine at full-run scale (nightly-scheduling note filed).

### 5. Evaluation/methods changes
1. **Ledger**: clean row-7 append. No migration.
2. **Leaderboard**: refreshed, no winner change (parity run confirms). Snapshot added (by design).
3. **No methods changes.** Lessons (both recorded in analysis): smoke scale hides payload caps (>1000-point write test now exists); RAGAS ±1pp run-to-run wobble needs paired per-Q comparison for small-win claims.

### 6. How to recall
- STEP file: `docs/progress/STEP_019_exp022_full_run.md`
- Row: `results/experiments.csv` line 8; per-Q: `results/exp_022_hybrid_qdrant/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260907_100551.json`
- Exp: `docs/experiments/exp_022_hybrid_qdrant/analysis.md`

### 7. Next step (STEP_020 candidate)
Product surface (FastAPI serving hybrid+Qdrant, then Streamlit demo) or rerank phase (exp_030 cross-encoder) or Vertex Search pre-deploy benchmark. Recommend FastAPI next: the system is deployable NOW — serving it surfaces real latency/cost numbers before further quality work.
