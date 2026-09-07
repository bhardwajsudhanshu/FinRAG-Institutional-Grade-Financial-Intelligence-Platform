# exp_030_flash_rerank

## Hypothesis

Hybrid retrieves the right chunks but doesn't always rank them first
(recall 0.88 vs citation 0.61 in exp_021). Pointwise Flash scoring over
the top-10 should re-order the answer-bearing chunk to the top, lifting
citation metrics toward recall WITHOUT moving recall (same 10
candidates, only re-ordered). Falsifiable either way: if citations don't
move, the gap is a generation (citer) problem, not ranking.

## Setup

- **Chunker**: `naive` (same 4447 — comparability with exp_021)
- **Retrieval**: `hybrid`, fetch top-10 candidates
- **Rerank**: `flash-pointwise` (Flash JSON 0–10 per pair, retrieval-score tie-break, top-5 kept)
- **Generator / judge**: unchanged. Eval v1 139 Q.

## What changes vs. exp_021

One variable: rerank on/off. Same chunks, same retrieval, same generator.

## Evaluation

Smoke (~8 min, 6 Q × 10 Flash calls — STEP_022):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid RERANK_BACKEND=flash-pointwise uv run python -m finrag.cli.eval --exp exp_030_flash_rerank --limit 6 --smoke
```

Full (~1.5h, 1390 Flash calls ≈ $0.11 + base ≈ $0.15 — STEP_023):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid RERANK_BACKEND=flash-pointwise VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_030_flash_rerank
```

(`VECTORDB_BACKEND` pinned: the machine OS env exports the invalid
`chroma`, which beats `.env` — STEP_020 finding. Always pin all four.)

Success = citation metrics rise toward recall, recall non-decreasing.
Results in `analysis.md` after the full run.
