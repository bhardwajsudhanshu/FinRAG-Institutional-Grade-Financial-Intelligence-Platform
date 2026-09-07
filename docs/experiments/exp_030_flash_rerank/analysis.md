# exp_030_flash_rerank — Analysis

**Status:** SCAFFOLDED (STEP_022). Full 139-Q run NOT yet executed — see STEP_023.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 7 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-07 10:51–10:56 UTC (312.9s wall), naive + hybrid + flash-pointwise,
`--exp exp_030_flash_rerank --limit 6 --smoke`.
Source: `results/smoke/exp_030_flash_rerank_20260907_105124/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 |
| context_recall / faithfulness / answer_relevancy | 1.00 / 0.975 / 0.7987 |
| hit@5 (chunk_id) / citation_accuracy | 0.667 / 0.667 |
| **hit@5_content / citation_content** | **0.833 / 0.833** (5/6) |
| mean_latency_ms / cost | 35927 (~36s/Q rerank scoring) / $0.0017 |

Findings: per-Q rows carry `hybrid` + `flash-pointwise`; 60 Flash scoring
calls ran clean (no parse failures sank anything visibly); only miss q_0005
(again — every configuration misses it). Latency confirms ADR-006's
~1.5h full-run estimate. First attempt died instantly on the machine-OS
`VECTORDB_BACKEND=chroma` (STEP_020's known trap — smoke command now pins
all four env vars; recorded so STEP_023's command includes it).

## Full run (TODO — STEP_023)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid RERANK_BACKEND=flash-pointwise uv run python -m finrag.cli.eval --exp exp_030_flash_rerank
make leaderboard
```

Then fill: headline table, citation-vs-recall gap verdict (the ADR-006
falsifiable bet), per-type split, cost accounting (~$0.15 most expensive
run yet).
