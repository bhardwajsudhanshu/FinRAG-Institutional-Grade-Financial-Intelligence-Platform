# exp_004_structural — Analysis

**Status:** SCAFFOLDED (STEP_010). Full 139-Q Vertex run NOT yet executed — see STEP_011.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 3 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-07 03:46–03:48 UTC (118.7s wall), `CHUNKER_STRATEGY=structural`,
`--exp exp_004_structural --limit 6 --smoke`, Vertex backend.
Source: `results/smoke/exp_004_structural_20260907_034645/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL 2025-10-31) / 141 |
| context_recall / faithfulness / answer_relevancy | 0.80 / 1.00 / 0.7797 |
| hit@5 (chunk_id) / citation_accuracy | 0.50 / 0.333 |
| **hit@5_content / citation_content** | **0.833 / 0.833** (5/6; OOS q_0006 True under fixed STEP_009 logic) |
| mean_latency_ms / cost | 6362 / $0.0016 |

Two findings:
1. **Index build 19.0s** for the same filing semantic needed 108.8s for — zero chunk-time embedding confirmed. Full 20-filing run should index in ~10 min (exp_002 territory), not ~64 min.
2. Per-Q: q_0001–q_0004 True, q_0005 section False (only miss), q_0006 OOS True. Small-n, but the dispatch + budgets + fixed OOS logic all work together first try.

## Full run (TODO — STEP_011)

```bash
CHUNKER_STRATEGY=structural uv run python -m finrag.cli.eval --exp exp_004_structural
make leaderboard
```

Then fill: headline table, per-type/per-ticker breakdowns, n_chunks vs
4447/5412/6858, verdict on context_recall (target > 0.8058) and
`hit_at_5_content` under fixed OOS logic (first clean number of the new
era — exp_003's 0.5612 was computed under v1 OOS logic; its fixed-logic
projection is 0.6906, see STEP_009 §5).
