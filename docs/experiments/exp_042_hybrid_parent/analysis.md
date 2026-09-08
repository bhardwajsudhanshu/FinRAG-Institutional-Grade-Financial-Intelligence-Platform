# exp_042_hybrid_parent — Analysis

**Status:** SCAFFOLDED (STEP_032). Full 139-Q run NOT yet executed — see STEP_033.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 10 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-08 08:55–08:57 UTC (132.6s wall), naive parents + hybrid-parent,
`--exp exp_042_hybrid_parent --limit 6 --smoke`.
Source: `results/smoke/exp_042_hybrid_parent_20260908_085520/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 parents (280 children, both sides) |
| context_recall / faithfulness / answer_relevancy | 1.00 / 0.9714 / 0.7823 |
| hit@5 (chunk_id) / citation_accuracy | 0.833 / 0.833 |
| **hit@5_content / citation_content** | **1.000 / 1.000 (6/6)** |
| mean_latency_ms / cost | 6207 / $0.0016 |

Findings: per-Q rows carry `hybrid-parent`; **second 6/6 in project
history, q_0005 True again** — child-space fusion reproduces parent-doc's
smoke exactly (same 6/6, same miss-free set). Small-n euphoria warning
stands double now — full run decides whether the combo beats both parents.

## Full run (TODO — STEP_033)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid-parent VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_042_hybrid_parent
make leaderboard
```

Then fill: headline table, both-single-variable verdicts (vs exp_041
0.6978 AND vs exp_021 0.8129), per-type split, cost-per-point reckoning
(3× index must buy its keep).
