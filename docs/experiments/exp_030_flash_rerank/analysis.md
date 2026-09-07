# exp_030_flash_rerank — Analysis

**Status:** COMPLETE (STEP_023). Full 139-Q run 2026-09-07 10:58–13:02 UTC (7384.5s pipeline, single attempt).
**Row:** `results/experiments.csv` row 8 (clean append; 4447 chunks — one variable vs exp_021).
**Per-Q:** `results/exp_030_flash_rerank/per_question.jsonl` (139 rows, all hybrid+flash-pointwise).
**Leaderboard:** SWEEP — leads all five decided categories (first 5/5 in project history).

## Headline (locked)

| Metric | exp_021 hybrid | **exp_030 +rerank** | Δ |
|---|---|---|---|
| n_chunks | 4447 | 4447 | — |
| context_recall | 0.8843 | **0.9132** | +2.9pp |
| faithfulness | 0.9063 | **0.9574** | +5.1pp |
| answer_relevancy | 0.7496 | **0.7864** | +3.7pp |
| hit@5 | 0.6763 | **0.7770** | +10.1pp |
| citation_accuracy | 0.6115 | **0.7266** | +11.5pp |
| hit@5_content | 0.8129 | **0.8849** | +7.2pp |
| citation_accuracy_content | 0.7986 | **0.8561** | +5.8pp |
| mean_latency_ms | 8961.5 | 41966.4 (~42s/Q) | the price |
| total_cost_usd (row = generation-only) | 0.0366 | 0.0380 | — |

## Gap verdict (ADR-006's falsifiable bet): RANKING, confirmed

Citations rose toward recall on both scales (chunk_id 0.61→0.73,
content 0.80→0.86) AND recall itself rose (0.88→0.91 — better-ordered
top-5 covers the judge's "enough to answer" bar more often). The gap was
ranking, not generation. No citer work needed; exp_031 cross-encoder is
now a cost/latency challenger, not a quality rescue.

## Per-type breakdown (content hit / cite)

lookup 67: **0.866** / 0.866 · section 45: **0.889** / 0.889 · synthesis 9: 0.778 / 0.778 · OOS 18: 1.000 / 0.778.

- Section 0.800→0.889: rerank's biggest win — paragraph-level Q's whose answer sat at rank 6–10 now surface.
- Lookup 0.776→0.866: exact-answer chunks promoted past near-miss neighbors.
- Synthesis flat 0.778: multi-chunk answers need *coverage*, not order — rerank can't fuse what retrieval didn't fetch together. Points at parent-doc / multi-query retrieval (Phase 3 leftovers), not more scoring.
- OOS cite 0.889→0.778 (14/18 refuse; 4 answered): reranked "relevant-looking" contexts tempt the model to answer unanswerables slightly more. Only regression in the row — small, honest, and the reason OOS exists as a type.

## Cost truth (row vs all-in)

Row `total_cost_usd` = $0.0380 covers generation ONLY (by design — the
runner accumulates `gen_result.cost_usd`). True run spend from
`data/runtime_costs.jsonl` (UTC stamps, run window): rerank **$0.0712**
(1390 calls) + generate $0.038 + embed $0.0622 = **$0.1714 all-in**.
ADR-006's ~$0.15 estimate was close (embed forgotten). Any future
cost/1K-Q math must use all-in, not the row. Not nightly-runnable at this
price/speed — a future nightly job runs plain hybrid; full rerank weekly at most.

## What this experiment teaches

1. **Ordering was the bottleneck, not retrieval or generation.** Same 4447 chunks, same retriever, same generator — only order changed, everything rose.
2. **42s/Q is the product question.** Quality solved; serving rerank per-query at 42s is not viable — answers: cache (repeat Q's), distill to cross-encoder (exp_031: MiniLM scores 10 pairs in ~1s CPU), or rerank-then-cache popular filings.
3. **Reranker category now defined** (`citation_accuracy`, STEP_023): exp_030 leads it (0.7266 vs 0.6115). `hit_at_10` placeholder retired without ever scoring a row.
4. No schema/code/eval-set changes for the run itself. No 429s, no multi-part errors this run.

## Run notes

Single attempt, 7384.5s. No kill, no rerun. Per-type detail above computed
from the canonical per-Q file (commands in STEP_023 file).

## Smoke result (6 Q, kept for the record)

2026-09-07 10:51–10:56 UTC (312.9s): content 0.833 (5/6, only miss q_0005),
60 Flash calls clean, $0.0017. Source:
`results/smoke/exp_030_flash_rerank_20260907_105124/` (untracked).

## Decision

**Rerank stays ON for quality leadership; OFF by default for cost.**
`rerank_backend` default remains `none` — nightly/cheap paths unchanged;
flagship evals and the demo's "best answer" mode opt into
flash-pointwise. exp_031 (MiniLM) decides whether leadership gets cheap.
