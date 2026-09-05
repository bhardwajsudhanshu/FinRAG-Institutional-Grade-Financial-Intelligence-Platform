# ADR-003: Eval Set Construction and Metric Selection

**Status:** Accepted
**Date:** 2026-09-05
**Deciders:** Project lead, FinRAG

## Context

FinRAG is a 12-week RAG project. Every chunking, retrieval, or vector-DB
experiment in Weeks 3-10 must be **scored** against the same fixed
benchmark, so the leaderboard at `results/leaderboard.json` is
comparable. This ADR fixes:

1. The **shape** of the eval set (count, distribution, sources)
2. The **generation procedure** (how the Q&A pairs are produced)
3. The **metric set** (RAGAS + custom)
4. The **schema** of `results/experiments.csv`

## Decision

### 1. Eval set: 200 Q&A pairs, verified, multi-type

**Count**: 200 Q&A pairs target, evenly distributed across 20 tickers
(one most-recent 10-K per ticker). 10 Q's per filing target; 8-12 actual
depending on filing size and verifier pass rate.

**Status (as of 2026-09-05, v1 frozen)**: 139 Q&A pairs covering all 20
tickers. The first full run was killed mid-generation at 139/200 (the
host process exited; we did not crash on a specific Q). Distribution
across types held steady: 48% lookup, 32% section, 13% OOS, 6%
synthesis. The set is frozen at 139 because:

- The 200-Q target was a 10-Q-per-filing ideal; some filings
  (e.g. COST, MSFT, PFE) only yielded 5-6 valid Q's before their
  sections ran out of citable material that the verifier would pass.
- 139 is well above the 100-Q minimum needed for hit@5 standard error
  ≈ 4% (per the locked metrics below). Topping up to 200 later is a
  non-breaking change: new Q's get fresh `q_NNNN` IDs and the CSV
  schema appends, not overwrites.
- Re-running the generator would re-generate *different* Q's (LLM
  temperature > 0), which would make the existing 139 stale.

So we freeze v1 = 139 and label it `eval_set_version: v1` in the
JSONL header. A future `v2` run can re-aim for 200 without breaking
this set.

**Distribution** (target → v1 actual):

| Type        | Target % | v1 Count | Example question |
|-------------|----------|----------|------------------|
| `lookup`    | 40%      | 67 (48%) | "What was Apple's revenue in FY2023?" |
| `section`   | 30%      | 45 (32%) | "What are Apple's main risk factors?" (from item 1a) |
| `synthesis` | 20%      | 9 (6%)   | "How does Apple's supply chain risk in item 1a relate to its revenue concentration disclosed in item 7?" |
| `out_of_scope` | 10%   | 18 (13%) | "What is Apple's market cap on Dec 31 2024?" (not in 10-K) |

**Section stratification** (within per-filing selection): `item_1`,
`item_1a`, `item_7`, `item_7a`, `item_8` — each filing's Q's cover at
least 3 of these 5 sections.

### 2. Generation procedure: 2-pass with verifier

Every Q&A pair has:
- A `source_chunk_id` (e.g. `AAPL_2025-10-31_item_7::0003`) matching what
  the production chunker produces
- A `source_span`: an exact substring from that chunk, ≤ 600 chars
- A `ground_truth_answer`: written by the LLM, with the constraint that
  it must be supported by `source_span`

**Pass 1 — generation**: `gemini-2.5-pro` (the strongest model) is given
a chunk and asked to produce a `{question, ground_truth_answer, source_span}`
triple in JSON. For synthesis Q's, 2-3 chunks are passed together.

**Pass 2 — verification**: `gemini-2.5-flash` (cheap) is given
`{question, ground_truth_answer, source_span}` and asked whether the
answer is supported by the span. We also run a deterministic
whitespace-tolerant substring check that `source_span` appears in the
chunk. A pair is `verified=true` only if both checks pass.

Pairs that fail verification are **dropped** (not corrected). The drop
rate is logged in the run summary.

### 3. Metrics: 3 RAGAS + 3 custom

RAGAS metrics (LLM-judged, computed via `ragas.evaluate()`):

- **context_recall**: did the retrieved chunks contain enough info to
  answer the question? (uses ground truth as the reference)
- **faithfulness**: is the generated answer supported by the retrieved
  chunks? (catches hallucination)
- **answer_relevancy**: is the generated answer actually on-topic?
  (uses an embedder to score similarity between generated Q's derived
  from the answer and the original question)

Custom metrics (no LLM judge, cheap):

- **hit_at_5**: fraction of Q's where the source chunk is in the top-5
  retrieved. For `out_of_scope` Q's, the inverse: the source chunk is
  *not* retrieved (we expect the model to refuse).
- **citation_accuracy**: fraction of Q's where the generated answer's
  citations include the source chunk. For OOS, "correct" means no
  citations + the answer starts with "I cannot".
- **mean_latency_ms**: end-to-end wall-clock per Q, including
  retrieval + generation.

### 4. CSV schema (frozen)

`results/experiments.csv` columns (locked, append-only):

```
exp_name, timestamp, n_questions, n_filings, n_chunks,
context_recall, faithfulness, answer_relevancy,
hit_at_5, citation_accuracy, mean_latency_ms, total_cost_usd
```

New metrics append at the end (never reorder, to keep pandas readers
backward-compatible). Missing values are written as empty strings
(RAGAS's `None` for metrics it skipped).

### 5. LLM judge for RAGAS

- **LLM judge**: `gemini-2.5-flash` via Vertex AI (cheap, fast, same auth
  as the rest of the project)
- **Embedding judge**: `text-embedding-005` via Vertex AI (needed for
  `answer_relevancy`)

Both are wrapped in `LangchainLLMWrapper` / `LangchainEmbeddingsWrapper`
for the RAGAS 0.4.x API.

## Rationale

### Why a fixed 200-Q set and not just ad-hoc testing

- **Comparability**: every experiment must score the same Q's, so the
  leaderboard column is monotonic over time
- **Manual review**: 200 Q's is small enough to spot-check by hand but
  big enough to be statistically meaningful (hit@5 standard error ≈ 3.5%)
- **Stability**: the same chunks must be produced by every chunker, so
  `source_chunk_id` is the join key between eval set and retrieval

### Why gemini-2.5-pro for generation, flash for verification

- Pro is the strongest open-weight commercial model on grounded Q-gen
  (avoids the "I can also mention..." hallucination common in smaller
  models)
- Flash is ~16× cheaper than Pro. Verification is a yes/no decision;
  Flash handles it well. Total cost of the 200-Q set: ~$3 Pro + $0.20
  Flash.

### Why these 3 RAGAS metrics, not 7

- **context_recall** directly measures retrieval quality — the single
  most important variable for RAG end-to-end
- **faithfulness** catches hallucination, which is the #1 production
  failure mode for LLM-based RAG
- **answer_relevancy** catches the "model retrieved the right chunk
  but answered the wrong question" failure mode
- We skip RAGAS `context_precision`, `context_entity_recall`, and
  `answer_correctness` because they overlap with the above and
  roughly double the per-Q judge cost

### Why OOS Q's are evaluated differently

Standard RAGAS metrics assume every Q has a correct answer in the
context. OOS Q's don't. We:
- Exclude OOS Q's from RAGAS scoring (the `ragas_rows` list filters them)
- Score OOS on a binary "did the model say I cannot find this?" via
  `citation_accuracy`
- Count OOS as a "hit" in `hit_at_5` if the source chunk is *not* in
  the top-5 (correct behavior for our system)

## Consequences

- The eval set is **frozen** at first creation. Future experiments can
  add new Q's (tracked by ID prefix) but cannot modify or remove
  existing ones. Old Q's that fall out of date (e.g. a chunker change
  breaks their source_chunk_id) are marked `deprecated` not deleted.
- Every experiment run increments `n_questions` and `n_filings` if the
  eval set grows, but the metric columns are forward-compatible.
- The 200-Q set is the single source of truth. If a future experiment
  appears to do dramatically better on a per-Q basis than the leader
  suggests, the Q is suspect — the verifier is the second line of
  defense.

## Alternatives considered

- **Crowd-sourced Q&A** (e.g. MTurk): too slow, too noisy, too expensive
  for a portfolio project. LLM-generated + LLM-verified has been
  validated by Anthropic (contextual retrieval) and Google's RAG
  cookbooks.
- **Public RAG benchmark** (e.g. HotpotQA, Natural Questions): wrong
  domain. We need to test on financial filings, not Wikipedia.
- **Live user feedback** (thumbs up/down): no users yet; will revisit
  in Week 12 once the Streamlit demo is up.

## References

- RAGAS 0.4.x docs: https://docs.ragas.io/en/stable/
- Anthropic contextual retrieval (Q-gen with self-citation check):
  https://www.anthropic.com/news/contextual-retrieval
- ADR-002 (Vertex AI choice — same auth, same LLM, same embeddings)
