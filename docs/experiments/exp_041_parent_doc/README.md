# exp_041_parent_doc

## Hypothesis

Small children retrieve precisely (exact sentence match), large parents
generate with context (surroundings intact). vs exp_001 (same 512/50
parents, retrieved directly), parent-doc should win section/synthesis
Q's whose answers span paragraph boundaries, and may lose lookup Q's
(one chunk already holds the fact — indirection adds noise). Parents
are byte-identical to exp_001 chunks, so this isolates hierarchy alone.
Numbered exp_041 (040 stays reserved for RAPTOR; both are indexing-family).

## Setup

- **Chunker**: parents naive 512/50 (= exp_001 chunks); children naive 256/25 within parents
- **Retrieval**: `parent-doc` (dense cosine over children → unique parents, best-child score, top-5 parents)
- **Generator / judge**: unchanged. Eval v1 139 Q. No rerank (rerank readily composes later if this wins).

## What changes vs. exp_001

| Component | exp_001 | exp_041 |
|---|---|---|
| Indexed units | 4447 parents | ~9K children (parents kept as generation contexts) |
| Retrieved contexts | parent chunks directly | parents via child hits |
| Generator input | same shape | same shape (512-token parents) |

## Evaluation

Smoke (~4 min, AAPL only — STEP_030):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=parent-doc VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_041_parent_doc --limit 6 --smoke
```

(`chunker_strategy` is ignored with a warning — parents pin naive. `VECTORDB_BACKEND` pinned: machine-OS `chroma` trap.)

Full (~50 min — children double the embedding bill — STEP_031):

```bash
# same env, no --limit/--smoke
```

Bars: section/synthesis content-hit above exp_001 (0.689/0.333 chunk_id terms); lookup must not collapse. Results in `analysis.md` after the full run.
