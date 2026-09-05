# exp_002_recursive

## Hypothesis

LangChain's `RecursiveCharacterTextSplitter` — which splits on `\n\n` (paragraph), then `\n` (line), then `. ` (sentence), then ` ` (word), then character — produces chunks that respect document structure better than the fixed-size naive window. This should improve `context_recall` (correct answer-bearing chunks make it into the top-k) and `hit_at_5` for paragraph-level questions, because an answer is more likely to live entirely inside one chunk.

The naive window slides by tokens with no awareness of structure: a single sentence can be split across two chunks, and a single chunk can contain 3-4 unrelated paragraphs glued together. Recursive chunking is the smallest, cheapest "structure-aware" upgrade.

## Setup

- **Chunker**: `recursive` (see `finrag/chunking.py::chunk_sections_recursive`)
- **chunk_size**: 2000 chars (~500 tokens — calibrated to match exp_001's 512-token budget)
- **chunk_overlap**: 200 chars (~50 tokens — matches exp_001's 50-token overlap)
- **Separators**: `["\n\n", "\n", ". ", " ", ""]` (paragraph → line → sentence → word → char)
- All other pipeline components are identical to exp_001 (same embedder, retriever, generator, eval set)

## What changes vs. exp_001

| Component | exp_001 | exp_002 |
|---|---|---|
| Chunker | naive (512 tok, fixed) | recursive (2000 char, paragraph-aware) |
| Chunker dispatched via | `chunker_strategy = "naive"` | `chunker_strategy = "recursive"` |
| Embedder / Retriever / Generator | identical | identical |
| Eval set | v1 (139 Q's, 20 tickers) | v1 (139 Q's, 20 tickers) |

The chunker dispatch (`finrag/chunking.py::chunk_sections_by_strategy`) selects the chunker at runtime from `settings.chunker_strategy`. The runner was wired in this session; chunks now carry `chunker: "naive" | "recursive"` in metadata so post-hoc analysis can filter by chunker.

## Why it might or might not help

- **Helps if**: many questions are about a single fact or paragraph (lookup / section questions). Answer is unlikely to span a paragraph boundary, so a paragraph-aligned chunk holds it intact.
- **Neutral if**: questions are about specific numerical values that happen to fall at a paragraph boundary in the 10-K. (Rare; 10-K tables are already in Item 8 which is its own section.)
- **Hurts if**: long, multi-paragraph answers (synthesis questions) need broader context. Recursive won't help because chunks are *smaller* on a paragraph boundary, not larger. (Mitigated by the same 200-char overlap as exp_001.)

## Evaluation

Run with:

```bash
CHUNKER_STRATEGY=recursive uv run python -m finrag.cli.eval --exp exp_002_recursive
```

Expected runtime: ~45 min (same as exp_001; chunking is faster than embedding, so total time is bounded by Vertex calls).

Results, per-type breakdown, and reasons for any delta vs. exp_001 will be in `analysis.md` after the run completes.
