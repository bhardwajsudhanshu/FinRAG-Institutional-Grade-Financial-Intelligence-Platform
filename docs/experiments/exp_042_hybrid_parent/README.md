# exp_042_hybrid_parent

## Hypothesis

exp_041 (dense children → parents) beats direct dense (+9.4pp) but trails
hybrid (+11pp): hierarchy without lexical signal can't find numbers/names
dense buries. Fusing dense+BM25 in CHILD space keeps both advantages —
exact child matches from BM25, paraphrase matches from dense — while
parents preserve generation context. vs exp_021 (hybrid on parents):
should match-or-beat on lookup/synthesis (finer retrieval units) without
losing section (same parents generate). vs exp_041: must beat content
0.6978, or the BM25 side adds nothing at child scale.

## Setup

- **Chunker**: parents naive 512/50 (= exp_001/041); children naive 256/25
- **Retrieval**: `hybrid-parent` (dense top-20 children + BM25 top-20 children → RRF k=60 → unique parents, best fused score → top-5)
- **Generator / judge**: unchanged. Eval v1 139 Q. No rerank.

## What changes vs. exp_041 / exp_021

| Component | exp_041 | exp_021 | exp_042 |
|---|---|---|---|
| Dense index | children | parents | children |
| BM25 index | — | parents | children |
| Fusion | — | RRF parents | RRF children → parents |
| Contexts | parents | parents | parents |

Single variable vs exp_041 (adds BM25 child side); single variable vs
exp_021 (moves both sides to children).

## Evaluation

Smoke (~5 min, AAPL only — STEP_032):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid-parent VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_042_hybrid_parent --limit 6 --smoke
```

(`chunker_strategy` ignored with warning — parents pin naive. `VECTORDB_BACKEND` pinned: machine-OS `chroma` trap.)

Full (~60 min, ~2× embed units — STEP_033):

```bash
# same env, no --limit/--smoke
```

Bars: content above exp_041 (0.6978) AND exp_021 (0.8129) to justify the
3× index. Results in `analysis.md` after the full run.
