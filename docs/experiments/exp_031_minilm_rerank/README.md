# exp_031_minilm_rerank

## Hypothesis

exp_030 proved ordering is the lever (cite 0.61→0.73). A local MiniLM
cross-encoder should match Flash's ordering at ~1/30th the latency and
$0 scoring cost: one batched CPU `predict` over 10 pairs (~1s) vs 10
sequential Flash JSON calls (~30s + $0.0005/Q). Quality bar: within
noise of exp_030 (content 0.8849, cite 0.7266). Cost bar: scoring $0.

## Setup

- **Chunker**: `naive` (same 4447 — three-way comparability)
- **Retrieval**: `hybrid`, fetch top-10 candidates
- **Rerank**: `cross-encoder` (`ms-marco-MiniLM-L-6-v2`, CPU, texts truncated to 2000 chars)
- **Generator / judge**: unchanged. Eval v1 139 Q.

## What changes vs. exp_030

One variable: the scorer (learned local vs LLM judge). Same candidates,
same generator. This is a cost/latency challenge, not a quality rescue —
exp_030 already won quality.

## Evaluation

Smoke (~4 min, 6 Q, CPU scoring, $0 scoring — STEP_024):

```bash
$env:HF_HOME='F:/.hf-cache'; $env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='hybrid'; $env:RERANK_BACKEND='cross-encoder'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_031_minilm_rerank --limit 6 --smoke
```

(`HF_HOME` keeps the ~90MB model off C: per the F:-drive discipline.
`VECTORDB_BACKEND` pinned: machine OS env exports invalid `chroma`.)

Full (~50 min — no per-pair LLM calls — STEP_025):

```bash
# same env, no --limit/--smoke
```

Bars: quality within noise of exp_030 AND scoring $0 / ~1s-per-10 latency.
Results in `analysis.md` after the full run.
