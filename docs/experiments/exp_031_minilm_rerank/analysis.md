# exp_031_minilm_rerank — Analysis

**Status:** COMPLETE (STEP_025). Full 139-Q run 2026-09-07 20:02–20:51 UTC (2959.4s pipeline, single attempt).
**Row:** `results/experiments.csv` row 9 (clean append; 4447 chunks — one variable vs exp_030).
**Per-Q:** `results/exp_031_minilm_rerank/per_question.jsonl` (139 rows, all hybrid+cross-encoder).
**Leaderboard:** unchanged (exp_030 still sweeps all 5 — correct).

## Headline (locked)

| Metric | exp_021 hybrid | exp_030 Flash rerank | **exp_031 MiniLM rerank** |
|---|---|---|---|
| n_chunks | 4447 | 4447 | 4447 |
| context_recall | 0.8843 | 0.9132 | 0.8430 |
| faithfulness | 0.9063 | 0.9574 | 0.8887 |
| answer_relevancy | 0.7496 | 0.7864 | 0.7027 |
| hit@5 | 0.6763 | 0.7770 | 0.6259 |
| citation_accuracy | 0.6115 | 0.7266 | 0.5683 |
| hit@5_content | 0.8129 | 0.8849 | **0.7698 (below no-rerank!)** |
| citation_accuracy_content | 0.7986 | 0.8561 | 0.7554 |
| mean_latency_ms | 8961.5 | 41966.4 | **9441.9 (~4.4× faster than Flash)** |
| total_cost_usd (row) | 0.0366 | 0.0380 | 0.0370 ($0 scoring confirmed) |

## Verdict: the challenger LOSES — ms-marco doesn't transfer to 10-Ks

MiniLM trails Flash on every column (content 0.770 vs 0.885, cite 0.568
vs 0.727, recall 0.843 vs 0.913) — and worse, trails PLAIN HYBRID
(0.813) by 4.3pp: reranking with it actively hurts. A web-passage
relevance model (ms-marco) mis-orders financial disclosure text: SEC
language ("material adverse effect", XBRL-adjacent tables) is out of its
training distribution, while Flash judges meaning directly. The ADR-006
"cheap leadership" thesis is falsified for this checkpoint — leadership
stays expensive (Flash $0.071/run scoring) or off (hybrid, free).

## Per-type breakdown (content hit / cite)

lookup 67: 0.701 / 0.701 (Flash 0.866 — MiniLM's worst gap: exact-number
answers need precise judges) · section 45: 0.800 / 0.800 (ties hybrid
exactly — no harm, no gain) · synthesis 9: 0.667 / 0.667 (below hybrid
0.778 — hurts multi-chunk most) · OOS 18: 1.000 / 0.889 (same as hybrid).

Pattern: the more exact the answer (lookup numbers), the more MiniLM
loses to Flash; where hybrid already saturates (section/OOS), it's neutral.

## Latency/cost ledger (the consolation, quantified)

9442ms/Q vs Flash's 41966ms/Q (**4.4× faster**), scoring $0 vs $0.0712.
End-to-end still ~9.4s/Q (generation + RAGAS dominate both), so the
rerank-stage win (seconds vs tens of seconds) matters only for serving,
not for eval wall-clock. All-in run cost ≈ $0.10 (gen $0.037 + embed
$0.062, no scoring) vs exp_030's $0.171.

## What this experiment teaches

1. **Negative results are results.** The phase compared learned-vs-LLM as ADR-006 framed it, and the answer is definitive on this domain: LLM judge wins, ms-marco loses, hybrid-alone sits between. No exp_031b with a bigger cross-encoder — the failure looks distributional (finance vs web), not capacity-shaped; a larger ms-marco model is unlikely to fix it. A finance-tuned cross-encoder (e.g. bge-reranker) would be the honest rematch, filed as optional.
2. **Smoke couldn't see this** (5/6 both at n=6 — identical). Small-n smoke proves plumbing, never quality. The methodology (smoke ≠ signal) held again.
3. No schema/code/eval-set changes. No failures (no 429s, no parse issues).

## Run notes

Single attempt, 2959.4s. Model loads once from `F:/.hf-cache`. Spend in
`data/runtime_costs.jsonl`; row $0.0370 generation-only (no `rerank` ops
logged at all — $0 scoring confirmed in the ledger itself).

## Smoke result (6 Q, kept for the record)

2026-09-07 19:43–19:46 UTC (160.1s): content 0.833 (5/6, same as Flash
smoke), $0 scoring. Source:
`results/smoke/exp_031_minilm_rerank_20260907_194343/` (untracked).

## Decision

**Rerank leadership = Flash (expensive) or OFF (hybrid, free). MiniLM
retired** (strictly dominated: worse than hybrid on quality, worse than
Flash on quality — its only win is scoring cost, which buys nothing
here). Rerank phase CLOSED unless a finance-tuned checkpoint appears.
