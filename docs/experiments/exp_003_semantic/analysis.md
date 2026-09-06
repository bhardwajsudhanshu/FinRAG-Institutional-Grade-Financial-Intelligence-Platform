# exp_003_semantic — Analysis

**Status:** SCAFFOLDED (STEP_007). Full 139-Q Vertex run NOT yet executed — see STEP_008.
**Smoke:** pending below. Canonical `results/experiments.csv` untouched (still 2 rows).

## Smoke result (5 Q, `--smoke`, ephemeral)

Run: 2026-09-06 21:12–21:16 UTC (230s wall), `CHUNKER_STRATEGY=semantic`,
`--exp exp_003_semantic --limit 5 --smoke`, Vertex backend.
Source: `results/smoke/exp_003_semantic_20260906_211228/smoke_experiments.csv`
(ephemeral — NOT in canonical `results/experiments.csv`).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 5 / 1 (AAPL 2025-10-31) / 141 |
| context_recall / faithfulness / answer_relevancy | 1.0 / 1.0 / 0.7669 |
| hit@5 (chunk_id) / citation_accuracy | 0.40 / 0.40 |
| **hit@5_content / citation_content** | **0.80 / 0.80** |
| mean_latency_ms / cost | 5073.8 / $0.0010 |

Two findings:
1. **Content vs chunk_id gap reproduces** (0.80 vs 0.40) — same artifact as
   exp_002, confirming STEP_006 fix measures the right thing on a new chunker.
2. **Index build is slow** (139s for 141 chunks + sentences): sentence
   embedding doubles Vertex calls. Full 139-Q/20-filing run will embed
   ~20× more sentences — budget ~45-60 min and ~$0.05-0.08 (vs $0.03-0.04
   for exp_001/002). Acceptable for one full run; batch size 20 is the
   bottleneck if we re-run often.

## Full run (TODO — STEP_008)

```bash
CHUNKER_STRATEGY=semantic uv run python -m finrag.cli.eval --exp exp_003_semantic
make leaderboard
```

Then fill: headline table (locked + content columns), per-type breakdown
(lookup/section/synthesis/OOS), per-ticker worst-5, n_chunks/latency/cost
vs exp_001 (4447 chunks) and exp_002 (5412 chunks), and verdict on whether
semantic beats recursive on `hit_at_5_content` (the decision metric for
the chunking track).
