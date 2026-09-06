# ADR-004: Retrieval Direction — BM25 Baseline, Then Hybrid RRF

**Status:** Accepted
**Date:** 2026-09-07
**Deciders:** Project lead, FinRAG

## Context

Chunking is 4/5 scored (STEP_011 verdict): no chunker beats naive on
`context_recall` (0.8058), semantic leads faithfulness, structural leads
content-hit + efficiency. Finer chunking has diminishing returns. The
exp_001 per-ticker analysis already predicted the next lever: narrative
filings (WMT, AMZN) where the dense embedder clusters "this is narrative"
instead of finding the specific fact — a lexical signal (numbers, names,
"Item 1A") should help exactly there. Time for Phase 3: retrieval.

## Decision

1. **exp_020 = BM25 baseline** (rank-bm25 `BM25Okapi`, regex word tokens,
   no embeddings at retrieval time) over **naive chunks** — isolates the
   retrieval effect against exp_001 (same 4447 chunks, same generator).
2. **exp_021 = hybrid dense + BM25 with Reciprocal Rank Fusion** (RRF,
   k=60, 20 candidates per side, top-5 fused) — same naive chunks.
3. New `retrieval_strategy` setting (`dense` | `bm25` | `hybrid`, default
   `dense`) selects the path in the eval runner; `dense` behavior is
   byte-identical to all frozen rows.
4. Vector-DB benchmarking (Qdrant/Weaviate/Vertex Search) stays a separate
   later phase — these experiments run on the in-memory indexes only, so
   retrieval quality is measured without infrastructure confounds.

## Rationale

- **BM25 first, not hybrid first:** hybrid beating dense proves nothing if
  we don't know each side's contribution. BM25-alone is the ablation.
- **RRF over weighted-score fusion:** dense cosine and BM25 scores live on
  incomparable scales; RRF fuses *ranks* (Cormack et al. 2009), needs no
  score normalization or learned weights, one parameter (k=60 standard).
- **Naive chunks for both:** keeps chunker fixed so rows compare purely on
  retrieval. Chunker × retriever cross-products come later (auto-router,
  Week 11).
- **rank-bm25, regex tokens:** zero new deps (already in pyproject), no
  NLTK data downloads, deterministic. English 10-K text needs nothing more.

## Consequences

- `finrag/retrieval.py` gains `BM25Index`, `build_bm25_index`,
  `reciprocal_rank_fusion`, `retrieve_with_strategy`; `InMemoryIndex` API untouched.
- `run_experiment` builds only the index(es) the strategy needs — pure-BM25
  runs embed nothing (fast, ~free retrieval; generation + RAGAS judge still bill).
- Same frozen metrics (RAGAS + hit@5 family incl. content columns under fixed
  OOS logic). `chunking_content`-style new categories only if needed; the
  `retrieval` leaderboard category (metric: context_recall) gets its first
  real contender in exp_021.
- Expected: BM25 wins lookup Q's with exact numbers/names; dense wins
  section/synthesis (paraphrase); hybrid wins overall. If hybrid fails to
  beat dense, the fallback is per-type routing (Week 11), not more fusion tuning.

## Alternatives considered

- **Dense-only + bigger top_k:** raises generator cost/noise without adding a missing signal. Rejected.
- **Learned sparse (SPLADE) / ColBERT:** explicitly out of scope (ADR-001) — operationally painful for the gain at this scale.
- **Cross-encoder re-rank instead:** that's Phase 4 (post-retrieval); it needs a strong candidate set first, which is this phase's job.

## References

- Cormack, Clarke, Buettcher 2009 (RRF): https://dl.acm.org/doi/10.1145/1571941.1572114
- exp_001 per-ticker analysis (`docs/experiments/exp_001_naive_baseline/analysis.md`)
- exp_004 decision (`docs/experiments/exp_004_structural/analysis.md`)
