# STEP_015 — exp_021 full run (139 Q): Phase 3 won

- **Date:** 2026-09-07 (06:27–07:13 UTC, 2729.4s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Both-bars verdict on hybrid; update every record the run changed.
- **Roadmap phase:** Week 5-8 Retrieval (Phase-3 in-memory COMPLETE — sweep)

### 1. Why
STEP_014 proved hybrid plumbing. ADR-004's bars (hit > 0.7194 AND recall >
0.8058) decide whether retrieval is solved or routing research begins.

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 6 `exp_021_hybrid_rrf` (clean append, 4447 chunks).
- `results/exp_021_hybrid_rrf/per_question.jsonl` — NEW, 139 rows (all hybrid).
- `results/leaderboard.json` — SWEEP: all four decided categories → exp_021 (`last_updated` 2026-09-07T07:13:22).
- `results/leaderboard_snapshots/leaderboard_20260907_071322.json` — NEW.
- `docs/experiments/exp_021_hybrid_rrf/analysis.md` — full analysis (both-bars, per-type/ticker, 4 lessons, Phase-3-complete decision).
- `docs/progress/STEP_015_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='hybrid'; uv run python -m finrag.cli.eval --exp exp_021_hybrid_rrf
uv run python tests/eval/update_leaderboard.py
```
Index 276.7s. No 429s, no multi-part errors, no kill — cleanest long run yet.

### 4. Result / numbers
139 Q / 20 filings / 4447 chunks; cr=**0.8843 (+8pp, best)**, fa=**0.9063 (best)**, ar=**0.7496 (best)**; hit@5=**0.6763 (best)**, cite=**0.6115 (best)**; **hit@5_content=0.8129 (best)**, cite_content=**0.7986 (best)**; 8961ms/Q; $0.0366. Lookup 0.776 / section **0.800** (recovers dense +11pp) / synthesis 0.778 (only non-lead, n=9, BM25 0.889) / OOS 1.000. AMZN 0.333→0.667 (clearest per-filing win); WMT still last at 0.500 (2× exp_001); 5 tickers perfect. Super-additive, not averaging — same 4447 chunks throughout, so the span is pure retrieval math.

### 5. Evaluation/methods changes
1. **Ledger**: clean row-6 append. No migration.
2. **Leaderboard**: first SWEEP in project history (4/4 decided). Rolling overwrite + immutable snapshot (by design).
3. **No methods changes.** Phase-3 verdict: hybrid RRF (k=60, untuned) is the production retrieval path.

### 6. How to recall
- STEP file: `docs/progress/STEP_015_exp021_full_run.md`
- Row: `results/experiments.csv` line 7; per-Q: `results/exp_021_hybrid_rrf/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260907_071322.json`
- Exp: `docs/experiments/exp_021_hybrid_rrf/analysis.md`

### 7. Next step (STEP_016 candidate)
Vector-DB benchmark behind the fixed hybrid interface (quality frozen → measures latency/ops only): Qdrant → Weaviate → Vertex Search, starting with ADR-005 (what "production-ready" means: p95 latency, cost/1K Q, ops burden). Requires `make docker-up` + vectordbs extra (already in pyproject).
