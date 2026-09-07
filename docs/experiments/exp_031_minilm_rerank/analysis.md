# exp_031_minilm_rerank — Analysis

**Status:** SCAFFOLDED (STEP_024). Full 139-Q run NOT yet executed — see STEP_025.
**Smoke:** below. Canonical `results/experiments.csv` untouched (still 8 rows).

## Smoke result (6 Q, `--smoke`, ephemeral)

Run: 2026-09-07 19:43–19:46 UTC (160.1s wall), naive + hybrid + cross-encoder,
`--exp exp_031_minilm_rerank --limit 6 --smoke` (`HF_HOME=F:/.hf-cache`).
Source: `results/smoke/exp_031_minilm_rerank_20260907_194343/` (untracked).

| Metric | Value |
|---|---|
| n_questions / n_filings / n_chunks | 6 / 1 (AAPL) / 97 |
| context_recall / faithfulness / answer_relevancy | 1.00 / 1.00 / 0.7997 |
| hit@5 (chunk_id) / citation_accuracy | 0.833 / 0.667 |
| **hit@5_content / citation_content** | **0.833 / 0.833** (5/6 — same as Flash smoke) |
| mean_latency_ms / cost | 6960 (~2.7 min wall vs Flash's 5.2 min) / $0.0017 ($0 scoring) |

Findings: per-Q rows carry `hybrid` + `cross-encoder`; model loads once
(~90MB cached); only miss q_0005 (universal). CPU scoring already ~2× the
Flash-smoke wall at n=6 — the latency thesis previews well. Full run decides.

## Full run (TODO — STEP_025)

```bash
$env:HF_HOME='F:/.hf-cache'; $env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='hybrid'; $env:RERANK_BACKEND='cross-encoder'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_031_minilm_rerank
make leaderboard
```

Then fill: headline table, quality-within-noise verdict vs exp_030
(content 0.8849 / cite 0.7266), latency ledger (per-Q rerank ms vs
Flash's ~30s/Q), $0-scoring confirmation.
