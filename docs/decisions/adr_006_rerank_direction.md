# ADR-006: Re-rank Direction — Pointwise Flash First, Cross-Encoder Second

**Status:** Accepted
**Date:** 2026-09-07
**Deciders:** Project lead, FinRAG

## Context

Retrieval is solved in the aggregate (hybrid sweeps, STEP_015) but a gap
persists inside every row: `context_recall` (0.88) vs `citation_accuracy`
(0.61) — the right chunks are often retrieved but not ranked first, so
generation cites (and the user reads) the wrong ones first. exp_001's
analysis forecast this step: re-ranking should close the recall↔citation
gap. The question is only which scorer.

## Decision

1. **exp_030 = pointwise Flash re-ranker**: retrieve top-10 with hybrid,
   score each (question, chunk) 0–10 with `gemini-2.5-flash` in JSON mode,
   keep top-5 by score (retrieval score breaks ties). No new dependencies.
2. **exp_031 = cross-encoder** (`ms-marco-MiniLM`, sentence-transformers +
   torch) IF exp_030 shows the gap is closable but Flash is too slow/costly
   — the learned-vs-LLM comparison is itself publishable. Deferred, not
   designed here.
3. **Candidates = 10, not 20**: 1390 Flash calls/run (~$0.10, +20–40 min)
   vs 2780 for top-20. RRF's top-10 already concentrates; rerank's job is
   ordering within it, not discovery beyond it.
4. New `rerank_backend` setting (`none` | `flash-pointwise`, default
   `none`) + `rerank_candidates: 10`. `none` is byte-identical to all
   frozen rows. Scorer is injectable (`score_fn`) so unit tests never call
   Vertex.

## Rationale

- **Flash over torch first:** zero new deps (torch is ~2GB on Windows and
  the #1 install-failure risk in the project so far), works with the
  existing auth/cost plumbing, directly comparable judge family
  (same-model scoring and generation is a known setup).
- **Pointwise over pairwise/listwise:** O(n) calls, trivially parallel
  later, deterministic to test (one score per pair). Listwise prompts are
  cheaper per Q but brittle to parse and order-sensitive.
- **JSON mode + tie-break by retrieval score:** scores tie constantly
  (integers 0–10 over 10 items); deterministic fallback keeps runs
  reproducible.
- **Gap-closing is falsifiable:** success = citation metrics rise toward
  recall with recall non-decreasing. If citations don't move, the gap is
  a generation problem (citer), not a ranking problem — that negative
  result routes to citer work, not more scorers.

## Consequences

- New `finrag/rerank.py` (`NoopReranker`, `FlashPointwiseReranker`,
  `get_reranker()`); runner applies it between retrieval and generation.
- Full exp_030 costs ~$0.15 (base $0.04 + ~$0.11 scoring) and runs ~1.5h.
  That's the most expensive run yet — approved once, not nightly.
- `reranker` leaderboard category (metric: `hit_at_10` placeholder) gets
  its real definition when exp_030 lands: propose `citation_accuracy`
  delta, recorded then.

## Alternatives considered

- **Cross-encoder first:** better $/run and latency, but torch install
  risk + a second new stack in one step. Deferred to exp_031 as the
  challenger, which makes the phase a comparison, not a single shot.
- **Cohere Rerank API:** external paid API, new vendor, new auth — against
  the Vertex-standardization bet (ADR-002). Rejected.
- **Listwise (one call ranks all 10):** ~14× fewer calls but prompt- and
  order-sensitive; keep as a fast-follow variant only if pointwise wins
  on quality but loses on cost.

## References

- exp_001 analysis (gap forecast), exp_021 analysis (hybrid bars)
- Nogueira & Cho 2019 (passage re-ranking with BERT — the original recipe)
