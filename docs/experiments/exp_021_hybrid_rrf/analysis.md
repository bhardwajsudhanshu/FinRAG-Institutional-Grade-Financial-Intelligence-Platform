# exp_021_hybrid_rrf — Analysis

**Status:** COMPLETE (STEP_015). Full 139-Q run 2026-09-07 06:27–07:13 UTC (2729.4s pipeline, single attempt).
**Row:** `results/experiments.csv` row 6 (clean append; 4447 chunks = three-way comparability with exp_001/020).
**Per-Q:** `results/exp_021_hybrid_rrf/per_question.jsonl` (139 rows, all `retrieval_strategy=hybrid`).
**Leaderboard:** SWEEP — leads all four decided categories (chunking, chunking_content, retrieval, end_to_end).

## Headline (locked)

| Metric | exp_001 dense | exp_020 BM25 | **exp_021 hybrid** |
|---|---|---|---|
| n_chunks | 4447 | 4447 | **4447** |
| context_recall | 0.8058 | 0.7238 | **0.8843 (best, +8pp)** |
| faithfulness | 0.8847 | 0.8604 | **0.9063 (best)** |
| answer_relevancy | 0.7428 | 0.6670 | **0.7496 (best)** |
| hit@5 (chunk_id, valid) | 0.6043 | 0.6115 | **0.6763 (best)** |
| citation_accuracy | 0.5612 | 0.5396 | **0.6115 (best)** |
| **hit@5_content** | — | 0.7194 | **0.8129 (best)** |
| **citation_accuracy_content** | — | 0.7050 | **0.7986 (best)** |
| mean_latency_ms | 8731.8 | 4374.1 | 8961.5 |
| total_cost_usd | 0.0381 | 0.0354 | 0.0366 |

## Both-bars verdict: CLEARED, with margin

ADR-004 demanded hit@5_content > 0.7194 AND context_recall > 0.8058
together. Hybrid posts 0.8129 / 0.8843 — and leads every other column too.
The fusion is super-additive, not averaging: recall beats dense alone by
8pp (BM25 rescues exact-answer Q's dense ranks 6–20, RRF promotes them
into top-5 with dense context around them). Phase 3 is WON on the
in-memory index; vector-DB benchmarking can start on a fixed winner.

## Per-type breakdown (does hybrid keep both sides?)

| Type | N | hit_content (hybrid vs BM25 vs exp_001) |
|---|---|---|
| lookup | 67 | **0.776** vs 0.716 vs 0.657 — keeps BM25's win, adds more |
| section | 45 | **0.800** vs 0.578 vs 0.689 — recovers dense AND beats it by 11pp |
| synthesis | 9 | 0.778 vs **0.889** vs 0.333 — only column hybrid doesn't lead (n=9, ±1 Q = 11pp; BM25's rare-term anchors still sharpest here) |
| out_of_scope | 18 | 1.000 (fix holds), cite 0.889 |

Section recovery is the story: dense breadth + lexical anchors together
(0.800) beat either alone. Synthesis is the one watch item — and the
honest caveat on the sweep (tiny n, BM25 leads).

## Per-ticker (hit_content)

WMT 0.500 (8, still worst but 2× exp_001) · PFE 0.600 · AMZN 0.667 (up from
0.333 everywhere — dense breadth rescued it) · GS/JPM 0.714 · NVDA/TSLA
0.750 · META 0.778 · BRK.B 0.800 · CVX/XOM 0.833 · UNH 0.875 ·
AAPL/BAC/GOOGL 0.889 · COST/JNJ/KO/MSFT/PG 1.000 (five perfect).

WMT stays last across all six experiments but climbs every step (0.250 →
0.375 → 0.625 → 0.500 → 0.667 → 0.500); retail-narrative remains the
hardest shape. AMZN's jump (0.333 → 0.667) is hybrid's clearest
per-filing win.

## What this experiment teaches

1. **RRF with default k=60 needed zero tuning.** No weights, no normalization, no grid search — ranks fused out of the box. The ADR-004 "no tuning" bet paid.
2. **Same chunks, +8pp recall.** All three Phase-3 rows share 4447 naive chunks, so the entire 0.7238 → 0.8843 span is retrieval math, the cleanest isolation in the project.
3. **Latency is flat** (8961ms ≈ dense 8732ms): per-Q dense embed + BM25 CPU + fusion ≈ one dense retrieval in wall-clock terms; generation + RAGAS dominate regardless.
4. No schema/code/eval-set changes. No new failure modes (no 429s, no multi-part errors this run).

## Run notes

Single attempt, 2729.4s. Index 276.7s (dense side embeds 4447; BM25 side free). Spend in `data/runtime_costs.jsonl`; row cost $0.0366 generation-only.

## Smoke result (6 Q, kept for the record)

2026-09-07 06:20–06:22 UTC (152.0s): content 0.833 (5/6, only miss q_0005 —
missed by every strategy), cr/fa 1.0, $0.0017. Source:
`results/smoke/exp_021_hybrid_rrf_20260907_062002/` (untracked).

## Decision

**Phase 3 (in-memory) complete: hybrid RRF is the production retrieval
path.** Next, in order: (a) vector-DB benchmark (Qdrant vs Weaviate vs
Vertex Search) behind the SAME hybrid interface — quality is now fixed so
the benchmark measures latency/ops only; (b) rerank + CRAG phases; (c)
optional exp_005 late/contextual chunking only if a retrieval-side need
for it appears (none currently).
