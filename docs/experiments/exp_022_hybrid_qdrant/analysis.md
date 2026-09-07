# exp_022_hybrid_qdrant — Analysis

**Status:** SCAFFOLDED (STEP_018). Full 139-Q run NOT yet executed — see STEP_019.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 6 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-07 08:58–09:01 UTC (146.9s wall), naive + hybrid + live
Qdrant, `--exp exp_022_hybrid_qdrant --limit 6 --smoke`.
Source: `results/smoke/exp_022_hybrid_qdrant_20260907_085855/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 |
| context_recall / faithfulness / answer_relevancy | 1.00 / 0.8963 / 0.7770 |
| hit@5 (chunk_id) / citation_accuracy | 0.833 / 0.667 |
| **hit@5_content / citation_content** | **0.833 / 0.833** (5/6 — identical to in-memory hybrid smoke) |
| mean_latency_ms / cost | 6091 / $0.0017 |

Findings: per-Q rows carry `hybrid` + `qdrant`; index 27.6s (embed + live
upsert 97); only miss q_0005 (same as in-memory hybrid). End-to-end path
works first try — full run decides parity vs exp_021.

## Full run (TODO — STEP_019)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid VECTORDB_BACKEND=qdrant uv run python -m finrag.cli.eval --exp exp_022_hybrid_qdrant
make leaderboard
```

Then fill: headline table, retrieved-set overlap vs exp_021 per-Q (the
parity proof), metrics-within-noise verdict, mean_latency comparison
(Qdrant dense side should shave ~1.3s/Q off retrieval).
