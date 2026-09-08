# exp_041_parent_doc — Analysis

**Status:** SCAFFOLDED (STEP_030 — the progress step; not exp_030). Full 139-Q run NOT yet executed — see STEP_031.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 9 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-08 07:25–07:27 UTC (128.3s wall), naive parents + parent-doc
dense, `--exp exp_041_parent_doc --limit 6 --smoke`.
Source: `results/smoke/exp_041_parent_doc_20260908_072550/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 parents (280 children indexed) |
| context_recall / faithfulness / answer_relevancy | 1.00 / 1.00 / 0.7703 |
| hit@5 (chunk_id) / citation_accuracy | 0.833 / 0.833 |
| **hit@5_content / citation_content** | **1.000 / 1.000 (6/6)** |
| mean_latency_ms / cost | 6795 / $0.0017 |

Findings: per-Q rows carry `parent-doc`; **first 6/6 in project history —
including q_0005, which dense, structural, BM25, hybrid, and both
rerankers all miss.** AAPL: 97 parents → 280 children (~2.9× retrieval
units). Small-n euphoria warning applies (smoke ≠ signal), but the
q_0005 flip is exactly the hypothesized mechanism (child isolates the
sentence, parent supplies surroundings) — full run decides.

## Full run (TODO — STEP_031)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=parent-doc VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_041_parent_doc
make leaderboard
```

Then fill: headline table, section/synthesis-vs-lookup split (the
hypothesis), parent/child counts, verdict vs exp_001 (same parents —
pure hierarchy effect).
