# exp_021_hybrid_rrf

## Hypothesis

exp_020 proved the split: BM25 leads content-hit (0.7194, exact spans)
but trails context_recall (0.7238, narrow top-5); dense leads recall
(0.8058) but buries exact facts. RRF-fused hybrid (top-20 per side,
k=60) should take **both bars at once**: BM25's exactness + dense's
breadth in one top-5. This is the most important run in the project so
far — if hybrid clears 0.7194 hit AND 0.8058 recall, Phase 3 is won and
vector-DB benchmarking starts on a fixed winner. ADR-004 fallback if it
fails: per-type routing (Week 11), not more fusion tuning.

## Setup

- **Chunker**: `naive` (same 4447 chunks — three-way comparability with exp_001/020)
- **Retrieval**: `hybrid` (dense top-20 + BM25 top-20 → RRF k=60 → top-5)
- **Generator / judge**: unchanged. top_k=5, eval v1 139 Q.

## What changes vs. exp_001 / exp_020

| Component | exp_001 | exp_020 | exp_021 |
|---|---|---|---|
| Retrieval | dense | BM25 | hybrid RRF |
| Per-Q embed | 1 (question) | 0 | 1 (dense side) |
| Index build | embed 4447 | 58s CPU | embed 4447 (dense side) |

## Evaluation

Smoke (~5 min, AAPL only):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid uv run python -m finrag.cli.eval --exp exp_021_hybrid_rrf --limit 6 --smoke
```

Full (~50 min — dense-side embedding returns — STEP_015):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid uv run python -m finrag.cli.eval --exp exp_021_hybrid_rrf
```

Bars: hit@5_content > 0.7194 AND context_recall > 0.8058. Results in
`analysis.md` after the full run.
