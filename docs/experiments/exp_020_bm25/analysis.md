# exp_020_bm25 — Analysis

**Status:** SCAFFOLDED (STEP_012). Full 139-Q run NOT yet executed — see STEP_013.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 4 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-07 05:01–05:02 UTC (108.8s wall), `CHUNKER_STRATEGY=naive
RETRIEVAL_STRATEGY=bm25`, `--exp exp_020_bm25 --limit 6 --smoke`.
Source: `results/smoke/exp_020_bm25_20260907_050101/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 (= naive count — same chunks as exp_001) |
| context_recall / faithfulness / answer_relevancy | 1.00 / 0.9739 / 0.8012 |
| hit@5 (chunk_id) / citation_accuracy | 0.833 / 0.667 |
| **hit@5_content / citation_content** | **0.833 / 0.833** (5/6; chunk_id and content AGREE — naive IDs exist) |
| mean_latency_ms / cost | 3925 / $0.0016 |

Three findings:
1. **Index build 0.9s** (vs 19s structural / 109s semantic same filing) — zero-embedding retrieval confirmed; full run should finish in ~30 min.
2. Chunk_id and content metrics agree here (both 0.833) — the artifact only bites when chunker ≠ naive. BM25-over-naive is the one comparison where legacy columns stay valid.
3. Per-Q `retrieval_strategy=bm25` recorded — audit trail works. Only miss: q_0005 section (same Q structural missed).

## Full run (TODO — STEP_013)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=bm25 uv run python -m finrag.cli.eval --exp exp_020_bm25
make leaderboard
```

Then fill: headline table, lookup-vs-section split (the ADR-004 bet),
per-ticker check on WMT/AMZN (predicted BM25 helps most there), and the
per-side baseline exp_021 hybrid must beat.
