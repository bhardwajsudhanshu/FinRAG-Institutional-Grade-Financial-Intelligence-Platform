# exp_041_parent_doc — Analysis

**Status:** COMPLETE (STEP_031 — the progress step; not exp_031). Full 139-Q run 2026-09-08 07:32–08:25 UTC (3199.0s pipeline, single attempt).
**Row:** `results/experiments.csv` row 10 (clean append; 4447 parents + ~13.2K children indexed).
**Per-Q:** `results/exp_041_parent_doc/per_question.jsonl` (139 rows, all parent-doc dense).
**Leaderboard:** unchanged (exp_030 sweeps all 5 — correct).

## Headline (locked)

| Metric | exp_001 dense+parents | **exp_041 parent-doc** | Δ (pure hierarchy) |
|---|---|---|---|
| parents / children | 4447 / — | 4447 / ~13,168 | ~2.96× embed units |
| context_recall | 0.8058 | 0.7397 | -6.6pp |
| faithfulness | 0.8847 | **0.9233 (best non-rerank)** | +3.9pp |
| answer_relevancy | 0.7428 | 0.6989 | -4.4pp |
| hit@5 (chunk_id, valid) | 0.6043 | 0.5899 | -1.4pp |
| citation_accuracy | 0.5612 | 0.5324 | -2.9pp |
| hit@5_content | — (0.6043 id-equiv) | **0.6978** | +9.4pp vs naive |
| citation_accuracy_content | — | 0.6763 | best non-hybrid |
| mean_latency_ms | 8731.8 | 10238.7 | +1.5s (bigger index scan) |
| total_cost_usd | 0.0381 | 0.0375 | — |

## Split verdict (hypothesis graded): HALF-RIGHT

- Section 0.644 / synthesis 0.556: better than exp_001's chunk_id terms (0.689≈ / 0.333) on synthesis (+22pp), flat on section. The mechanism works where answers span boundaries — but only modestly.
- Lookup 0.672 vs exp_001's 0.657: held (no collapse — the feared indirection cost didn't materialize).
- Overall content 0.6978 ≈ structural 0.6906, well below hybrid 0.8129. Hierarchy helps dense (+9.4pp) but doesn't touch lexical+dense fusion. The smoke 6/6 (incl. q_0005) did NOT scale — small-n euphoria, as warned.
- Faithfulness 0.9233 is the best non-reranked number in the project (exp_021: 0.9063): parent contexts ground answers well even when retrieval is mid-tier. Grounded-but-narrow is parent-doc's signature.

## What this experiment teaches

1. **Hierarchy is real but small** (+9pp over direct dense, same parents). The remaining gap to hybrid (+11pp more) is lexical signal, not granularity — finer retrieval units without BM25 can't find numbers/names dense buries.
2. **Children cost 3× embeddings for +9pp** (~13.2K vs 4.4K units; index build 658s vs ~276s). Worst cost/point in the project so far. Only worth it combined with hybrid (children-BM25 + parent contexts) — filed as the natural follow-up, not built.
3. **STEP_014's multi-part fix fired live again** (07:54 UTC log) — second production save, no Q lost.
4. No schema/code/eval-set changes for the run. No 429s.

## Run notes

Single attempt, 3199.0s. Parents 4447 + children ~13,168 (per-filing log lines). Spend in `data/runtime_costs.jsonl`; row $0.0375 generation-only.

## Smoke result (6 Q, kept for the record)

2026-09-08 07:25–07:27 UTC (128.3s): content 1.000 (6/6, first ever incl.
q_0005), $0.0017. Source:
`results/smoke/exp_041_parent_doc_20260908_072550/` (untracked). Lesson
re-learned: smoke proves plumbing, never quality (6/6 → 0.698 at scale).

## Decision

**Parent-doc: useful, not leading.** Keeps best-non-rerank faithfulness crown; loses overall to hybrid by 11pp at 3× index cost. Ship only as hybrid+parent-doc combo IF that follow-up beats hybrid alone — else retired alongside MiniLM. Retrieval leftovers now: multi-query/HyDE (question-side, untested) and that combo.
