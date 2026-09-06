# exp_003_semantic

## Hypothesis

Sentence-level embedding-distance chunking keeps semantically coherent
sentences together and cuts only where meaning shifts (cosine-distance
spike ≥ P95). vs exp_001 naive (fixed windows) and exp_002 recursive
(punctuation boundaries), this should improve `hit_at_5_content` and
`context_recall` on section and synthesis Q's, where the answer lives
inside one topic block, not one paragraph.

Naive splits mid-sentence; recursive respects punctuation but not topic.
Semantic is the first chunker that looks at *meaning*.

## Setup

- **Chunker**: `semantic` (see `finrag/chunking.py::semantic_chunk_text`)
- **Sentence split**: regex `(?<=[.!?])\s+` + blank lines
- **Embed sentences**: `get_embedder().embed_batch` (Vertex text-embedding-005 on real runs, mock offline)
- **Breakpoint**: consecutive cosine distance ≥ 95th percentile within the section
- **Budget**: max 512 tokens / chunk, 1-sentence overlap (≈50-token budget), oversized sentences fall back to naive split
- **Metadata**: `chunker="semantic"`, `semantic_threshold_p=95.0`
- All other pipeline components identical to exp_001/002 (same retriever, generator, eval set v1 139 Q)

## What changes vs. exp_001 / exp_002

| Component | exp_001 | exp_002 | exp_003 |
|---|---|---|---|
| Chunker | naive 512/50 tokens | recursive 2000/200 chars | semantic 512 tok + P95 split |
| Dispatch | `naive` | `recursive` | `semantic` |
| Cost | 1× embed | 1× embed | ~2× embed (sentences + chunks) |
| Eval columns | chunk_id only | chunk_id only | chunk_id + `*_content` (STEP_006 fix) |

## Evaluation

Smoke (cheap, ~$0.002, ~1 min):

```bash
CHUNKER_STRATEGY=semantic uv run python -m finrag.cli.eval --exp exp_003_semantic --limit 5 --smoke
```

Full (Vertex, ~45 min, ~$0.04 — STEP_008):

```bash
CHUNKER_STRATEGY=semantic uv run python -m finrag.cli.eval --exp exp_003_semantic
```

Scored on locked metrics + new `hit_at_5_content` / `citation_accuracy_content`
(the trustworthy cross-chunker signals from STEP_006).
Results + per-type breakdown go in `analysis.md` after the full run.
