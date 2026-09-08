# exp_043_multi_query — Analysis

**Status:** COMPLETE (STEP_035). Full 139-Q run 2026-09-08 10:35–12:00 UTC (5084.8s pipeline, single attempt).
**Row:** `results/experiments.csv` row 12 (clean append; 4447 chunks — one variable vs exp_001).
**Per-Q:** `results/exp_043_multi_query/per_question.jsonl` (139 rows, all dense+multiquery).
**Leaderboard:** unchanged (exp_030 sweeps all 5 — correct).

## Headline (locked)

| Metric | exp_001 dense | **exp_043 +multiquery** | Δ |
|---|---|---|---|
| n_chunks | 4447 | 4447 | — |
| context_recall | 0.8058 | 0.8003 | -0.6pp (noise) |
| faithfulness | 0.8847 | **0.9199** | +3.5pp |
| answer_relevancy | 0.7428 | 0.7317 | -1.1pp (noise) |
| hit@5 | 0.6043 | 0.5755 | -2.9pp |
| citation_accuracy | 0.5612 | 0.5252 | -3.6pp |
| hit@5_content | — (0.6043 id-equiv) | **0.7194** | — |
| citation_accuracy_content | — | 0.6978 | — |
| mean_latency_ms | 8731.8 | 25152.7 (~25s/Q) | expansion + 4× retrieval |
| total_cost_usd | 0.0381 | 0.0378 | +~$0.01 expansion (invisible in row) |

## Concentration verdict (the whole point): NO — uniform noise, retire

Honest non-OOS slice (121 Q's, OOS counted 18/18 by design in both eras):
exp_001 dense hits 78, exp_043 hits 82 — net **+4, with 9 gained and 5
lost** (discordant 9-vs-5, p≈0.42 by McNemar reasoning — not significant).
Gains do NOT concentrate in lexical-gap Q's; they scatter. The expansion
premium (~$0.01 + 3× latency) buys statistical noise. **Retire
multi-query on dense.**

Two curiosities, both recorded without overclaiming:
1. Content 0.7194 = exp_020's 0.7194 EXACTLY (100/139 both) — but per-Q
   overlap is only 82 shared, 18 unique each way. Same score, different
   Q's: dense+expansion and BM25 find substantially DIFFERENT answer sets.
   Union would be 118/139 = 0.849 — unachievable by fusion without an
   oracle, but it motivates hybrid+multiquery as the one combo not yet
   tried (filed, low priority: hybrid already covers most of both sets).
2. Faithfulness 0.9199 is 2nd-best non-rerank (parent-doc 0.9233 first):
   fused multi-formulation contexts ground well. Consistent with the
   pattern that broader context → faithful answers.

## Per-type breakdown (content hit / cite)

lookup 67: 0.672 / 0.672 · section 45: 0.689 / 0.689 (exactly exp_001's
section number — eerie, and a reminder that section-level paraphrase
rarely beats the original) · synthesis 9: 0.667 / 0.667 · OOS 18:
1.000 / 0.833.

No type concentrates the gains — the retire condition, met.

## What this experiment teaches

1. **Question-side expansion without teeth.** Flash paraphrases of
   already-clear analyst questions add formulations, not information —
   the eval Q's are well-formed (LLM-written from the answers!), so
   vocabulary mismatch barely exists in v1. Multi-query would matter more
   on real user queries (typos, slang, fragments) — v1 can't show it.
   Honest scope note, not an excuse: on THIS benchmark it's noise.
2. **McNemar thinking for paired rows.** Same-139-Q comparisons should
   count discordant pairs (9-vs-5), not headline deltas. Adopted as standard.
3. No schema/code/eval-set changes. No failures (no 429s, no multi-part).

## Run notes

Single attempt, 5084.8s. 139 expansion calls (~$0.01, invisible in the
$0.0378 row — generation-only accounting again). Spend in
`data/runtime_costs.jsonl`.

## Smoke result (6 Q, kept for the record)

2026-09-08 10:22–10:26 UTC (207.8s): content 1.000 (6/6, third ever),
$0.0017. Source:
`results/smoke/exp_043_multi_query_20260908_102254/` (untracked). Fourth
data point for smoke-is-plumbing.

## Decision

**Multi-query (dense) retired.** Stays in the codebase as an orthogonal
flag (zero cost when off, composes with hybrid for a possible follow-up),
but no full-run mandate. Retrieval family status: hybrid stands;
parent-doc retired; BM25 ablation recorded; multi-query retired on dense.
Remaining: hybrid+multiquery combo (filed, low priority), HyDE (untested).
