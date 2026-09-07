# exp_020_bm25 — Analysis

**Status:** COMPLETE (STEP_013). Full 139-Q run 2026-09-07 05:36–06:07 UTC (1827.1s pipeline, single attempt).
**Row:** `results/experiments.csv` row 5 (clean append; 4447 chunks = exp_001 count, isolation confirmed).
**Per-Q:** `results/exp_020_bm25/per_question.jsonl` (139 rows, all carry `retrieval_strategy=bm25`).
**Leaderboard:** takes `chunking_content` (0.7194); `retrieval` stays exp_001.

## Headline (locked)

| Metric | exp_001 dense+naive | exp_004 structural | **exp_020 bm25+naive** |
|---|---|---|---|
| n_chunks | 4447 | 4952 | **4447** (identical — pure retrieval effect) |
| context_recall | 0.8058 | 0.7727 | 0.7238 (lowest yet) |
| faithfulness | 0.8847 | 0.8826 | 0.8604 |
| answer_relevancy | 0.7428 | 0.7340 | 0.6670 (lowest yet) |
| hit@5 (chunk_id, valid here) | 0.6043 | 0.3957 | **0.6115 (best)** |
| citation_accuracy (chunk_id) | 0.5612 | 0.2806 | 0.5396 |
| **hit@5_content** | — | 0.6906 | **0.7194 (best)** |
| **citation_accuracy_content** | — | 0.6691 | **0.7050 (best)** |
| mean_latency_ms | 8731.8 | 8908.1 | **4374.1 (fastest full run)** |
| total_cost_usd | 0.0381 | 0.0327 | 0.0354 |

## The split: best hit, worst recall

BM25 is simultaneously the content-hit leader (0.7194) and the
context_recall trailer (0.7238). Both true, no contradiction: BM25
surfaces chunks containing the exact answer span (rare terms match hard)
but its top-5 are lexically tight and context-poor — the RAGAS judge,
asking "is there *enough* here to answer", votes no more often than for
dense top-5s that carry surrounding narrative. **Precision (span found)
vs context (enough to answer)** is the retrieval tradeoff this phase must
resolve — the textbook case for hybrid: dense brings breadth, BM25 brings
exactness. exp_021's bar is now quantified: beat 0.7194 content-hit AND
0.8058 context_recall simultaneously.

## Per-type breakdown (ADR-004 bets graded)

| Type | N | hit_id | hit_content | cite_content |
|---|---|---|---|---|
| lookup | 67 | 0.672 | 0.716 ( beats exp_001 0.657) | 0.716 |
| section | 45 | 0.511 | 0.578 ( trails exp_001 0.689) | 0.578 |
| synthesis | 9 | 0.778 | **0.889 (8/9, crushes all dense)** | 0.889 |
| out_of_scope | 18 | 0.556 | 1.000 (fix holds) | 0.889 |

- Lookup ✓ and section ✓ exactly as ADR-004 predicted (exact strings vs paraphrase).
- Synthesis 0.889 was UNpredicted: synthesis Q's fuse distinctive rare terms from 2+ chunks ("Blackwell Ultra" + "MI400"), and BM25 matching both beats dense paraphrase matching neither precisely. Lesson: multi-hop-ish Q's over same-filing chunks favor lexical anchors.
- OOS hit_id 0.556 (source not retrieved 10/18) is *correct* behavior counted as hit — BM25 is less trigger-happy than dense on competitor-name queries.

## Per-ticker (hit_content)

AMZN 0.333 (9, still worst — narrative defeats both sides) · BAC 0.556 · GS 0.571 · MSFT/PFE 0.600 · **WMT 0.625 (up from 0.250 exp_001 / 0.375 exp_003)** ✓ · CVX/META 0.667 · PG 0.714 · NVDA/TSLA/UNH 0.750 · GOOGL 0.778 · KO/XOM 0.833 · JPM 0.857 · AAPL 0.889 · BRK.B/COST/JNJ 1.000.

WMT recovery confirms the ADR-004 mechanism (retail-narrative filings hide facts from embeddings; numbers/names retrieve them). AMZN immobile suggests its misses aren't lexical either — possibly question-side (its Q's may hinge on section synthesis BM25 can't bridge alone → hybrid test).

## Robustness note (new failure mode, first occurrence)

q_0053 generation failed: Flash returned TWO identical text parts and the
SDK's `.text` accessor raised ("Multiple content parts are not supported").
Runner caught it (empty answer, row scored, run continued) — the catch
worked as designed. Proposed STEP_014 micro-fix: join `response.parts`
texts in `VertexGenerator.generate` instead of trusting `.text`. 1/139 Q
affected; no metric materially changes, but nightly runs shouldn't depend
on SDK accessor luck.

## Run notes

Single attempt, 1827.1s. Index 58s for all 20 filings (vs 275s structural, 3840s semantic). Latency 4374ms/Q — fastest full run (zero per-Q embedding). Category note: `chunking_content` leadership now sits with a *retrieval* experiment — the category tracks the metric, not the axis (rename to `content_hit` only with a future locked schema rev, not now).

## Smoke result (6 Q, kept for the record)

2026-09-07 05:01–05:02 UTC (108.8s): content = chunk_id = 0.833 (agree —
naive IDs valid), index 0.9s, $0.0016. Source:
`results/smoke/exp_020_bm25_20260907_050101/` (untracked).

## Decision

BM25-alone is a legitimate contender (content-hit leader, cheapest index),
but its recall/answer_relevancy trail rules it out solo. **exp_021 hybrid
RRF is now the most important run in the project**: it must combine
dense's 0.8058 recall with BM25's 0.7194 hit. If hybrid clears both bars,
Phase 3 is won and vector-DB benchmarking can start on a fixed winner.
