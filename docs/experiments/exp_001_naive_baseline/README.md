# exp_001 — Naive baseline

**Status:** Complete (2026-09-05)
**Result row:** `results/experiments.csv`
**Per-Q details:** `results/exp_001_naive_baseline/per_question.jsonl`

## Hypothesis

A vanilla RAG pipeline (naive fixed-size chunker, dense retrieval, Flash
generation) is the floor. Every other chunker / retriever / re-ranker
must beat this on `context_recall` and `faithfulness` to justify its
complexity.

## Configuration

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Chunking   | Naive fixed-size, 512 tokens, 50-token overlap (tiktoken cl100k_base) | Standard "first thing you'd try"; baseline reference. |
| Embedder   | `text-embedding-005` via Vertex AI (768-dim) | ADR-002 stack. |
| Vector DB  | In-memory cosine similarity over NumPy | No external dep; Phase 3 swaps this for Qdrant/Weaviate/Vertex. |
| Generator  | `gemini-2.5-flash` via Vertex AI | ADR-002 stack; cheap and fast. |
| top_k      | 5 | ADR-003 spec. |
| Eval set   | `data/eval/qa_pairs.jsonl` (v1, 139 Q's, 20 filings) | ADR-003 spec. |
| RAGAS judge | `gemini-2.5-flash` (LLM) + `text-embedding-005` (emb) | ADR-003 spec. |

## Result

| Metric | Value |
|--------|-------|
| n_questions | 139 |
| n_filings | 20 |
| n_chunks | 4447 |
| **context_recall** | 0.8058 |
| **faithfulness** | 0.8847 |
| **answer_relevancy** | 0.7428 |
| **hit@5** | 0.6043 |
| **citation_accuracy** | 0.5612 |
| mean_latency_ms | 8731.8 |
| total_cost_usd | 0.0381 |

`hit@5=0.60` and `citation_accuracy=0.56` are the headline numbers.
They say: even with Flash generating carefully-cited answers, naive
chunking loses the source chunk in the top-5 ~40% of the time, and
~44% of answers don't include the right citation. These are the gaps
exp_002-006 (better chunking) and exp_020+ (better retrieval) are
designed to close.

## What did not work

- **Synthesis Q's**: 9 Q's in the eval set asked for cross-section
  synthesis. The naive retriever's top-5 rarely covers both source
  sections, so context_recall drops disproportionately on this slice.
  See `analysis.md` for the per-type breakdown.
- **Long filings**: JPM (605 chunks) and GS (530 chunks) have the
  worst hit@5 — the naive 512-token chunker produces too many
  sub-100-token tail chunks that get embedded as low-similarity
  noise.

## Cost

$0.038 total for 139 Q's ($0.27 per 1000 Q's). The bulk is
embedding ($0.025, 4447 chunks) plus RAGAS judge LLM calls
($0.010). Generator is essentially free.

## Next experiment

`exp_002_recursive` will switch to recursive character splitting
(LangChain's `RecursiveCharacterTextSplitter`, 512/50) — cheapest
possible improvement to test whether the bad hit@5 is from the
naive tokenizer boundary, not from a structural problem with the
data.
