# exp_044_hyde — Analysis

**Status:** COMPLETE (STEP_040). Full 139-Q run 2026-09-08 15:35–16:49 UTC (4392.3s pipeline, single attempt).
**Row:** `results/experiments.csv` row 13 (clean append; 4447 chunks — one variable vs exp_001).
**Per-Q:** `results/exp_044_hyde/per_question.jsonl` (139 rows, all dense+hyde).
**Leaderboard:** unchanged (exp_030 sweeps all 5 — correct).

## Headline (locked)

| Metric | exp_001 dense | **exp_044 +HyDE** | Δ |
|---|---|---|---|
| n_chunks | 4447 | 4447 | — |
| context_recall | 0.8058 | **0.8140** | +0.8pp |
| faithfulness | 0.8847 | **0.9024** | +2.5pp |
| answer_relevancy | 0.7428 | 0.7512 | +0.7pp |
| hit@5 | 0.6043 | 0.5899 | -1.4pp |
| citation_accuracy | 0.5612 | 0.5396 | -2.2pp |
| hit@5_content | — (0.6043 id-equiv) | **0.7482** | — |
| citation_accuracy_content | — | **0.7194 (= BM25 exactly)** | — |
| mean_latency_ms | 8731.8 | 20127.8 (~20s/Q) | HyDE write + 2× retrieval |
| total_cost_usd | 0.0381 | 0.0377 (+139 HyDE calls invisible in row) | — |

## Vague-Q verdict: SUGGESTIVE, not decisive — KEEP (don't retire)

Honest non-OOS slice (121 Q's): exp_001 hits 78, HyDE hits 86 — net +8
with 13 gained / 5 lost (discordant 13-vs-5, p≈0.10 by McNemar
reasoning). Twice multiquery's net (+4, 9-vs-5, p≈0.42), same direction,
stronger. Below the significance bar, above the noise floor — the middle
verdict multiquery didn't earn. Per-type: lookup 0.716 (= BM25 exactly),
section 0.711, synthesis 0.667, OOS 1.000/0.778 — gains spread evenly,
no type concentrates them (so no "vague-Q" sub-story either; the lift is
broad and thin).

Curiosities, recorded without overclaiming:
1. cite_content 0.7194 ties BM25's cite_content EXACTLY (98/139 both) —
   third exact-tie of the project (after 0.8129×2 and 0.7194×2). The
   ledger loves round coincidences at n=139.
2. RAGAS recall 0.8140 noses past naive's 0.8058 — HyDE is the only
   dense-side change that lifts recall at all (parent-doc lowered it).
3. Faithfulness 0.9024 ≈ hybrid tier (0.9063): hypothetical-doc contexts
   ground well.

## What this experiment teaches

1. **HyDE > multiquery, both < hybrid.** Question-side ranking: HyDE +8
   net (p≈0.10) vs multiquery +4 (p≈0.42) vs hybrid's +17 over dense.
   Keep HyDE available (flag stays, zero cost off); retire nothing yet —
   hybrid+HyDE combo is the one untried union (filed, low priority, same
   oracle caveat as the multiquery-combo note).
2. **McNemar again decides.** Headline +14.4pp (0.6043→0.7482) mixes eras
   (chunk_id vs content + OOS redesign); the paired non-OOS +8 is the
   honest number. Standard holds.
3. No schema/code/eval-set changes. No failures (no 429s, no multi-part).

## Run notes

Single attempt, 4392.3s. 139 HyDE writes (~$0.01, `hyde_write` ops in
cost log, invisible in the $0.0377 row — generation-only accounting
again). Spend in `data/runtime_costs.jsonl`.

## Smoke result (6 Q, kept for the record)

2026-09-08 15:25–15:28 UTC (174.9s): content 1.000 (6/6, fifth ever),
$0.0017. Source:
`results/smoke/exp_044_hyde_20260908_152535/` (untracked). Fifth data
point for smoke-is-plumbing.

## Decision

**HyDE stays available, not default.** Best dense-only config (0.748 >
parent-doc 0.698 > multiquery-dense 0.719?? — no: 0.748 > 0.719, so HyDE
beats multiquery head-to-head too). Order dense-side options: HyDE
(0.748) > multiquery (0.719) > parent-doc (0.698) > direct (0.604) — all
below hybrid (0.813). Question-side work closes with HyDE kept.
