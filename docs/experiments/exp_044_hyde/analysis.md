# exp_044_hyde — Analysis

**Status:** SCAFFOLDED (STEP_039). Full 139-Q run NOT yet executed — see STEP_040.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 12 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-08 15:25–15:28 UTC (174.9s wall), naive dense + HyDE,
`--exp exp_044_hyde --limit 6 --smoke`.
Source: `results/smoke/exp_044_hyde_20260908_152535/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 |
| context_recall / faithfulness / answer_relevancy | 1.00 / 0.85 / 0.7716 |
| hit@5 (chunk_id) / citation_accuracy | 0.667 / 0.667 |
| **hit@5_content / citation_content** | **1.000 / 1.000 (6/6)** |
| mean_latency_ms / cost | 17345 (~17s/Q — HyDE write + 2× retrievals) / $0.0017 |

Findings: per-Q rows carry `dense` + `hyde=true`; **fifth 6/6,
q_0005 True again** — the AAPL slice no longer discriminates anything
(five straight perfect smokes across five different mechanisms).
Faithfulness 0.85 (lowest smoke-faithfulness yet — one answer wobbled)
is the only crack. Full run decides everything.

## Full run (TODO — STEP_040)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=dense HYDE_ENABLED=true VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_044_hyde
make leaderboard
```

Then fill: headline table, vague-Q concentration check, verdict vs
exp_001 (content 0.6043 id-valid), all-in cost note (HyDE calls logged
as `hyde_write`, invisible in the row).
