# exp_021_hybrid_rrf — Analysis

**Status:** SCAFFOLDED (STEP_014). Full 139-Q run NOT yet executed — see STEP_015.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 5 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-07 06:20–06:22 UTC (152.0s wall), `CHUNKER_STRATEGY=naive
RETRIEVAL_STRATEGY=hybrid`, `--exp exp_021_hybrid_rrf --limit 6 --smoke`.
Source: `results/smoke/exp_021_hybrid_rrf_20260907_062002/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 |
| context_recall / faithfulness / answer_relevancy | 1.00 / 1.00 / 0.7827 |
| hit@5 (chunk_id) / citation_accuracy | 0.833 / 0.667 |
| **hit@5_content / citation_content** | **0.833 / 0.833** (5/6) |
| mean_latency_ms / cost | 6152 / $0.0017 |

Findings: hybrid path works first try (index 18.9s — dense side embeds 97
chunks, BM25 side free); per-Q `retrieval_strategy=hybrid` recorded. Only
miss q_0005 — the same Q dense, structural, and BM25 all miss (genuinely
hard, not strategy-specific). No signal yet at n=6 — full run decides.

## Full run (TODO — STEP_015)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid uv run python -m finrag.cli.eval --exp exp_021_hybrid_rrf
make leaderboard
```

Then fill: headline table, both-bars verdict (hit@5_content > 0.7194 AND
context_recall > 0.8058), per-type split (does hybrid keep BM25's lookup +
synthesis AND recover dense's section?), WMT/AMZN check.
