# exp_043_multi_query

## Hypothesis

User questions often mismatch filing vocabulary ("How much money did
Apple make?" vs "net sales were $383.3 billion"). Three Flash
paraphrases + original, retrieved independently and RRF-fused, should
recover Q's where one formulation misses — mostly lookup/section with
lexical gaps. Orthogonal flag over a dense base (one variable vs
exp_001); hybrid+multiquery follows only if this wins.

## Setup

- **Chunker**: `naive` (same 4447 — comparability with exp_001)
- **Retrieval**: `dense` + `multiquery` (3 Flash paraphrases, RRF fuse 4 rankings → top-5)
- **Generator / judge**: unchanged. Eval v1 139 Q. No rerank.

## What changes vs. exp_001

One variable: question expansion on/off. Same chunks, same dense index,
same generator. Extra cost: 1 Flash call/Q (~$0.01/run) + 3× retrievals
(free, in-memory).

## Evaluation

Smoke (~4 min, AAPL only — STEP_034):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=dense MULTIQUERY_ENABLED=true VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_043_multi_query --limit 6 --smoke
```

(`chunker_strategy` naive pinned by design here. `VECTORDB_BACKEND` pinned: machine-OS `chroma` trap.)

Full (~50 min + expansion calls — STEP_035):

```bash
# same env, no --limit/--smoke
```

Bars: content above exp_001's 0.6043 (chunk_id-valid baseline) with
recall non-decreasing; per-type check that gains concentrate in
lexical-gap Q's, not uniform noise. Results in `analysis.md` after the
full run.
