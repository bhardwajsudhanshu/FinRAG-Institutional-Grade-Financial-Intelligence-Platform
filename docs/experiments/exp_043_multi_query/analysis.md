# exp_043_multi_query — Analysis

**Status:** SCAFFOLDED (STEP_034). Full 139-Q run NOT yet executed — see STEP_035.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 11 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-08 10:22–10:26 UTC (207.8s wall), naive dense + multiquery,
`--exp exp_043_multi_query --limit 6 --smoke`.
Source: `results/smoke/exp_043_multi_query_20260908_102254/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 |
| context_recall / faithfulness / answer_relevancy | 1.00 / 0.9333 / 0.7744 |
| hit@5 (chunk_id) / citation_accuracy | 0.833 / 0.833 |
| **hit@5_content / citation_content** | **1.000 / 1.000 (6/6)** |
| mean_latency_ms / cost | 19350 (~19s/Q — expansion + 4× retrievals) / $0.0017 |

Findings: per-Q rows carry `dense` + `multiquery=true`; **third 6/6,
q_0005 True again** — the AAPL slice is now saturated (every config
since parent-doc goes 6/6 or 5/6 here; discriminative power exhausted).
Full run decides; per-type concentration analysis is the whole verdict.

## Full run (TODO — STEP_035)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=dense MULTIQUERY_ENABLED=true VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_043_multi_query
make leaderboard
```

Then fill: headline table, gain-concentration check (lexical-gap Q's vs
uniform noise), verdict vs exp_001 (content 0.6043 id-valid), cost note
(~$0.01 expansion premium).
