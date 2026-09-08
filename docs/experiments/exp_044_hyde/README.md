# exp_044_hyde

## Hypothesis

Short vague questions embed poorly ("How much money did Apple make?"
shares little vocabulary with "net sales were $383.3 billion"). A Flash
-written hypothetical 10-K excerpt speaks filing language, so
document-to-document similarity should beat question-to-document —
fused with the original ranking as anchor against hallucinated
specifics. One variable vs exp_001 (dense base, same chunks, same
generator). If HyDE wins, the follow-up is hybrid+HyDE; if not,
question-side work is done (multiquery retired, HyDE retired).

## Setup

- **Chunker**: `naive` (same 4447 — comparability with exp_001)
- **Retrieval**: `dense` + `hyde` (Flash hypothetical passage → dispatcher second query → RRF fuse → top-5)
- **Generator / judge**: unchanged. Eval v1 139 Q. No rerank.

## What changes vs. exp_001

One variable: hypothetical-doc fusion on/off. Same chunks, same dense
index, same generator. Extra cost: 1 Flash call/Q (~$0.01/run, logged as
`hyde_write` — invisible in the generation-only row, counted in all-in).

## Evaluation

Smoke (~4 min, AAPL only — STEP_039):

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=dense HYDE_ENABLED=true VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_044_hyde --limit 6 --smoke
```

(`chunker_strategy` naive pinned by design here. `VECTORDB_BACKEND` pinned: machine-OS `chroma` trap.)

Full (~50 min + 139 HyDE calls — STEP_040):

```bash
# same env, no --limit/--smoke
```

Bars: content above exp_001's 0.6043 (chunk_id-valid) with recall
non-decreasing; per-type check (vague-Q gains vs uniform noise).
Results in `analysis.md` after the full run.
