# exp_001 — Analysis

Generated 2026-09-05 from `results/exp_001_naive_baseline/per_question.jsonl`.

## Headline

- **hit@5=0.604**, **faithfulness=0.885**, **context_recall=0.806**
- 60% of the time the source chunk is in the top-5 retrieved
- 88% of the time the answer is supported by retrieved context
- 56% of the time the cited chunks include the source chunk

The gap between context_recall (0.81) and citation_accuracy (0.56)
is the most interesting signal: the retriever often has the right
context, but the generator picks a different chunk to cite. The
likely cause is Flash anchoring on a topic-relevant chunk that
isn't the exact answer-bearing one.

## Per-type breakdown

| Type          | N  | hit@5 | citation_accuracy |
|---------------|----|-------|-------------------|
| `lookup`      | 67 | 0.657 | 0.657             |
| `section`     | 45 | 0.689 | 0.689             |
| `out_of_scope`| 18 | 0.667 | 0.667             |
| `synthesis`   |  9 | 0.333 | 0.333             |

- **`synthesis`** is the outlier: 33% hit@5. The naive 512-token
  retriever's top-5 almost never covers both source sections of a
  cross-section synthesis Q. exp_004 (late chunking) and exp_040
  (RAPTOR) are the structural fixes.
- **`section`** is best (69%): when the Q is about a whole section,
  the naive retriever surfaces the right region consistently.
- **`out_of_scope`** is at 67%, which is correct by design (the
  source chunk is *not* in top-5, so we count that as a "hit" for
  the OOS metric). See ADR-003 §3.

## Per-ticker breakdown (worst 5)

| Ticker | hit@5 | N | Notes |
|--------|-------|---|-------|
| WMT    | 0.250 | 8 | 10-K is mostly retail-narrative, not numbers |
| AMZN   | 0.333 | 9 | Long narrative sections dilute the embedding space |
| PFE    | 0.400 | 5 | Pharma narrative is paragraph-heavy |
| GS     | 0.429 | 7 | 530 chunks — too much tail noise |
| NVDA   | 0.500 | 8 | Dense technical jargon, embedding collision |

The pattern: filings with long, narrative-dense sections
(retail, pharma, investment banks) hurt the most. The 512-token
chunker splits mid-paragraph, and the embeddings cluster into
"this is narrative" rather than "this contains the specific fact."

## Latency

Mean 8.7s/Q. Decomposed roughly as:

- Retrieval (cosine over 4447 vectors): ~0.2s
- Embed (cached after first call): ~0s
- Generation (Flash, 5 chunks in context, ~3K tokens out): ~5-6s
- RAGAS judge (3 calls × 0.5-1s each): ~2-3s

The RAGAS judge is ~30% of latency. If we ever need faster nightly
runs, batching the judge calls reduces this to ~1s/Q.

## What this means for downstream experiments

- **exp_002 (recursive)**: should bump hit@5 by 5-10 points
  (paragraph-boundary respect).
- **exp_004 (late chunking)**: the synthesis-type gain is the
  main bet; +20 points on synthesis could lift the overall
  hit@5 from 0.60 to 0.65.
- **exp_020+ (BM25, hybrid)**: ticker-level diversity suggests
  the dense embedder alone is missing the BM25 signal for
  numbers/names — hybrid should help WMT, AMZN most.
- **exp_030 (re-ranker)**: even a cheap cross-encoder should
  close the gap between context_recall (0.81) and citation_accuracy
  (0.56) by re-ordering the top-5 so the cited chunk surfaces.
