# exp_042_hybrid_parent — Analysis

**Status:** COMPLETE (STEP_033). Full 139-Q run 2026-09-08 09:08–10:04 UTC (3367.8s pipeline, single attempt).
**Row:** `results/experiments.csv` row 11 (clean append; 4447 parents + ~13.2K children).
**Per-Q:** `results/exp_042_hybrid_parent/per_question.jsonl` (139 rows, all hybrid-parent).
**Leaderboard:** unchanged (exp_030 sweeps all 5 — correct).

## Headline (locked)

| Metric | exp_041 parent-doc | exp_021 hybrid | **exp_042 combo** |
|---|---|---|---|
| parents / children | 4447 / ~13.2K | 4447 / — | 4447 / ~13.2K |
| context_recall | 0.7397 | 0.8843 | 0.8223 |
| faithfulness | 0.9233 | 0.9063 | 0.9190 |
| answer_relevancy | 0.6989 | 0.7496 | 0.7245 |
| hit@5 | 0.5899 | 0.6763 | **0.6835 (best chunk_id)** |
| citation_accuracy | 0.5324 | 0.6115 | **0.6187 (best chunk_id)** |
| hit@5_content | 0.6978 | 0.8129 | **0.8129 (exact tie)** |
| citation_accuracy_content | 0.6763 | 0.7986 | 0.7842 |
| mean_latency_ms | 10238.7 | 8961.5 | 10562.9 |
| total_cost_usd | 0.0375 | 0.0366 | 0.0366 |

## Both-bars verdict: ONE of two (tie, not win)

- vs exp_041 (0.6978): **CLEARED** (+11.5pp) — the BM25 child side contributes enormously; hierarchy alone was starved of lexical signal.
- vs exp_021 (0.8129): **TIED EXACTLY** (113/139 both) — not beaten. Best chunk_id hit/cite (0.6835/0.6187) and faithfulness 0.9190 are consolation leads, all within noise of sibling runs.
- Verdict: PARTIAL redemption. The combo proves hierarchy + lexical fuse cleanly (no interference — the fear was mutual dilution), but 3× index cost buys zero headline gain over hybrid. Not a serving upgrade.

## Per-type breakdown (content hit / cite)

lookup 67: 0.791 / 0.791 · section 45: 0.778 / 0.778 · synthesis 9: 0.778 / 0.778 · OOS 18: 1.000 / 0.778.

- Section 0.644→0.778 and synthesis 0.556→0.778 vs exp_041: the combo delivers exactly where parent-doc was supposed to — child-space BM25 finds the anchors, parents hold the coverage.
- Lookup 0.791 is the best lookup slice anywhere (BM25-alone 0.716, hybrid unmeasured here but implied similar).
- OOS cite 0.778 (4 answered — same small regression as exp_030's reranked contexts tempting answers).

## What this experiment teaches

1. **Fusion composes, granularity doesn't dominate.** Same fused math at two granularities → identical headline (0.8129 twice). Retrieval quality lives in the *signals fused* (dense+lexical), not the *unit size*.
2. **The 6/6 smokes are officially noise** (three 6/6s → 0.698/0.813/0.813 at scale). Smoke's job is plumbing proof — it has now failed as signal three times running. Methodology note, not news.
3. **Hierarchy retires (again, finally).** Useful finding (parent contexts ground best), not competitive: hybrid matches it free of hierarchy cost. Remaining retrieval ideas: multi-query/HyDE (question-side) — or stop; retrieval is solved enough.
4. One RAGAS-retry 429 (auto-recovered). No code/schema/eval-set changes. No kill.

## Run notes

Single attempt, 3367.8s. Parents 4447 + children ~13.2K embedded (index build embedded both). Spend in `data/runtime_costs.jsonl`; row $0.0366 generation-only.

## Smoke result (6 Q, kept for the record)

2026-09-08 08:55–08:57 UTC (132.6s): content 1.000 (6/6, second ever),
$0.0016. Source:
`results/smoke/exp_042_hybrid_parent_20260908_085520/` (untracked).

## Decision

**Hierarchy retired; hybrid stands alone.** exp_042 ties hybrid at 3× cost — no serving case. Parent-doc's faithfulness crown (0.9233) stands as its epitaph. Retrieval phase: only question-side ideas (multi-query/HyDE) remain untested.
