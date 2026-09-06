# STEP_011 — exp_004 full run (139 Q) + ledger updates

- **Date:** 2026-09-07 (04:08–04:54 UTC, 2718.0s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Score structural on the frozen set; update every record the run changed.
- **Roadmap phase:** Week 3-4 Chunking (3/5 full runs done — 4/5 chunkers scored)

### 1. Why
STEP_010 smoke proved plumbing; the track decision needs the full row —
first clean new-era content number (fixed OOS logic) plus the context_recall
verdict on section-aware budgets.

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 4 `exp_004_structural` (clean append, no migration this time).
- `results/exp_004_structural/per_question.jsonl` — NEW, 139 rows.
- `results/leaderboard.json` — `chunking_content` → exp_004 (0.6906); `end_to_end` stays exp_003; `last_updated` 2026-09-07T04:54:08.
- `results/leaderboard_snapshots/leaderboard_20260907_045408.json` — NEW.
- `docs/experiments/exp_004_structural/analysis.md` — full analysis (§0.6906 coincidence, per-type/ticker, 4 lessons, decision: defer exp_005, start Phase 3 retrieval).
- `docs/progress/STEP_011_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='structural'; uv run python -m finrag.cli.eval --exp exp_004_structural
uv run python tests/eval/update_leaderboard.py
```
Single attempt, no kill. Index 275s (4952 chunks — as predicted, ~1/14 of semantic). One 429 during RAGAS, auto-retried in 4s, no data loss.

### 4. Result / numbers
139 Q / 20 filings / **4952 chunks**; cr=0.7727 (target >0.8058 MISSED), fa=0.8826, ar=0.7340; hit@5=0.3957/cite=0.2806 (artifacts); **hit@5_content=0.6906 = 96/139, exactly the STEP_009 projection** (non-OOS 78/121 = 0.645 identical to exp_003; whole delta is OOS fix); cite_content=0.6691 (identical to exp_003); synthesis 0.667 (6/9, best); OOS content 1.000 (fix at scale); 8908ms/Q; $0.0327. Ticker order churned (GS worst 0.286, KO 0.333→1.000 — 3000-char table windows likely kept numeric answers intact).

### 5. Evaluation/methods changes
1. **Ledger**: clean row-4 append (header already 14-col). No migration.
2. **Leaderboard**: `chunking_content` exp_003→exp_004; rest unchanged. Rolling overwrite + immutable snapshot (by design).
3. **No methods changes.** Quirk watch: first 429 backpressure — note for nightly runs (stagger judge / lower `ragas_batch_size` if recurrent).

### 6. How to recall
- STEP file: `docs/progress/STEP_011_exp004_full_run.md`
- Row: `results/experiments.csv` line 5; per-Q: `results/exp_004_structural/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260907_045408.json` snapshot
- Exp: `docs/experiments/exp_004_structural/analysis.md`

### 7. Next step (STEP_012 candidate)
Phase 3 retrieval.signature: BM25 baseline (`rank-bm25` dep already in pyproject) → hybrid RRF vs dense on the frozen set. Chunking 4/5 scored; exp_005 (late/contextual) deferred per analysis decision — record an ADR-004 (retrieval direction) before building.
