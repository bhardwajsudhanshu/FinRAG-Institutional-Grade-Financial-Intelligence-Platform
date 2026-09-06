# exp_003_semantic — Analysis

**Status:** COMPLETE (STEP_008). Full 139-Q Vertex run 2026-09-06 22:55 → 2026-09-07 00:40 UTC (6264.5s pipeline).
**Row:** `results/experiments.csv` row 3 (14-col schema — header migrated in STEP_008, see §6).
**Per-Q:** `results/exp_003_semantic/per_question.jsonl` (139 rows).
**Leaderboard:** `chunking_content` first winner = exp_003; `end_to_end` flips to exp_003 on faithfulness.

## Headline (locked)

| Metric | exp_001 naive | exp_002 recursive | **exp_003 semantic** |
|---|---|---|---|
| n_chunks | 4447 | 5412 | **6858** (+54% vs naive) |
| context_recall | 0.8058 | 0.7913 | 0.7562 |
| faithfulness | 0.8847 | 0.8595 | **0.8932 (best)** |
| answer_relevancy | 0.7428 | 0.7080 | 0.7103 |
| hit@5 (chunk_id) | 0.6043 | 0.3237 | 0.3237 (artifact — same cause as exp_002) |
| citation_accuracy (chunk_id) | 0.5612 | 0.2158 | 0.2302 (artifact, see §4) |
| **hit@5_content** | — (frozen) | — (frozen) | **0.5612** |
| **citation_accuracy_content** | — (frozen) | — (frozen) | **0.6691** |
| mean_latency_ms | 8731.8 | 9968.1 | 8861.8 |
| total_cost_usd (row = generation only) | 0.0381 | 0.0299 | 0.0301 |

## Per-type breakdown (content metrics)

| Type | N | hit_id | hit_content | cite_id | cite_content |
|---|---|---|---|---|---|
| lookup | 67 | 0.299 | 0.657 | 0.299 | 0.657 |
| section | 45 | 0.244 | 0.644 | 0.244 | 0.644 |
| synthesis | 9 | 0.111 | **0.556** | 0.111 | 0.556 |
| out_of_scope | 18 | 0.722 | 0.000 (quirk, see §4) | 0.000 (quirk) | 0.833 |

- **Synthesis 0.556** beats exp_001 (0.333) and exp_002 (0.000) on chunk_id terms and is close to exp_002's post-hoc ticker+section proxy (0.667) — the one place semantic clearly helps, as hypothesized.
- Lookup/section content-hit (~0.65) trails exp_001's chunk_id hit@5 (0.657/0.689), but that comparison is unfair: exp_001's IDs exist in its own index (see STEP_005). Like-for-like content scores for exp_001/002 don't exist (frozen rows, no texts stored) — exp_003's content columns are the new baseline future chunkers compare against.

## Per-ticker (hit_content, worst first)

AMZN 0.333 (9) · KO 0.333 (6) · WMT 0.375 (8) · BRK.B 0.400 (5) · PFE 0.400 (5) · AAPL 0.444 (9) · CVX 0.500 (6) · GOOGL 0.556 (9) · GS/JPM 0.571 (7) · MSFT 0.600 (5) · NVDA/UNH 0.625 (8) · BAC/JNJ/META/XOM 0.667 · PG 0.714 (7) · TSLA 0.750 (8) · COST 1.000 (2, tiny n).

Same pattern as exp_001: narrative-dense filings (retail, energy, conglomerates) hurt most. Semantic chunking did not fix the ticker skew.

## What this experiment teaches

1. **Semantic ≈ recursive on retrieval, best on faithfulness.** RAGAS context_recall regressed (-5pp vs naive) while faithfulness leads (0.8932). Interpretation: fewer, topic-coherent chunks → generator stays grounded even when the exact source span isn't top-5 (cite_content 0.669 is the best citation signal so far).
2. **P95 threshold over-fragments: 6858 chunks (+54%).** JPM 916, GS 782, BRK.B 613 semantic chunks. More chunks = denser index = noisier neighborhoods (the same mechanism as exp_002's +21.7%). A P99 or per-section-budget variant (exp_003b?) could keep the coherence win without the fragmentation cost.
3. **Latency didn't blow up** (8862ms ≈ naive 8732ms): brute-force cosine over 6858 vectors is still dwarfed by generation + RAGAS judge. Cost row cheapest yet ($0.0301, generation-only accounting).
4. **Two methods quirks found (no code changed — ledger immutable):**
   - OOS Q's carry `source_span='<no relevant span>'` (not empty as STEP_006 assumed), so the `not source_span` OOS branch never fires and OOS hit_content = 0.000 systematically, dragging overall 0.561 down (non-OOS content hit = 78/121 = **0.645**). Fix (treat placeholder as empty) proposed for STEP_009 — it changes the runner, so it must come with a re-run, not a rewrite.
   - Vertex generator always cites all top-5 contexts, so chunk_id citation_accuracy for OOS is structurally 0.000; content cite (0.833, "I cannot" check) is the honest OOS citation signal.

## Run notes (for reproducibility)

- Attempt 1 (21:25–22:5x UTC) killed by 90-min tool timeout mid-RAGAS (all 139 per-Q records survived via incremental write; no CSV row — CLI appends only after RAGAS). Attempt 2 (22:55–00:40 UTC, 6264.5s) completed. Both attempts' Vertex calls are logged in `data/runtime_costs.jsonl` (gitignored); the CSV row's cost covers generation only, by design (`ragas_runner.py` accumulates `gen_result.cost_usd`).
- Chunk counts per filing were deterministic across attempts (e.g. JPM 916, GS 782, AAPL 141) — semantic chunking is stable given the same embedder.

## Smoke result (5 Q, `--smoke`, ephemeral — kept for the record)

Run: 2026-09-06 21:12–21:16 UTC (230s wall). 5 Q / 1 filing / 141 chunks,
cr=1.0, fa=1.0, ar=0.7669, hit@5=0.40 vs hit@5_content=0.80, $0.0010.
Source: `results/smoke/exp_003_semantic_20260906_211228/` (untracked).
The content-vs-chunk_id gap previewed here reproduced at full scale.

## Decision for the chunking track

Semantic takes `chunking_content` (0.5612, first holder) and `end_to_end`
faithfulness (0.8932). Naive keeps `chunking`/`retrieval` on context_recall
(0.8058). Next: exp_004 structural (section-aware budgets) should target
context_recall + chunk count, not faithfulness.
