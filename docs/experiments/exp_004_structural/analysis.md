# exp_004_structural — Analysis

**Status:** COMPLETE (STEP_011). Full 139-Q Vertex run 2026-09-07 04:08–04:54 UTC (2718.0s pipeline, no rerun needed).
**Row:** `results/experiments.csv` row 4 (clean append under 14-col header — no migration).
**Per-Q:** `results/exp_004_structural/per_question.jsonl` (139 rows).
**Leaderboard:** takes `chunking_content` (0.6906); `end_to_end` stays exp_003.

## Headline (locked)

| Metric | exp_001 naive | exp_002 recursive | exp_003 semantic | **exp_004 structural** |
|---|---|---|---|---|
| n_chunks | 4447 | 5412 | 6858 | **4952** (in target band) |
| context_recall | 0.8058 | 0.7913 | 0.7562 | 0.7727 (target >0.8058 MISSED) |
| faithfulness | 0.8847 | 0.8595 | **0.8932** | 0.8826 |
| answer_relevancy | 0.7428 | 0.7080 | 0.7103 | 0.7340 |
| hit@5 (chunk_id) | 0.6043 | 0.3237 | 0.3237 | 0.3957 (artifact) |
| citation_accuracy (chunk_id) | 0.5612 | 0.2158 | 0.2302 | 0.2806 (artifact) |
| **hit@5_content** | — | — | 0.5612 (v1 OOS logic) | **0.6906 (fixed logic)** |
| **citation_accuracy_content** | — | — | 0.6691 | 0.6691 (identical) |
| mean_latency_ms | 8731.8 | 9968.1 | 8861.8 | 8908.1 |
| total_cost_usd (generation-only) | 0.0381 | 0.0299 | 0.0301 | 0.0327 |

## The 0.6906 coincidence (read this first)

exp_004's `hit_at_5_content` = 96/139 = **0.6906 — exactly the STEP_009
projection for exp_003 under fixed logic** (78 non-OOS + 18 OOS). Decomposed:
structural's non-OOS content-hits are 78/121 = 0.645 — *identical* to
exp_003's non-OOS 78/121. Same 78 hits on the same 121 Q's? Not verified
per-Q (different chunk sets), but the aggregate equality says: **per-section
budgets and embedding-distance splits retrieve answer-bearing text equally
well; the entire exp_003→exp_004 content delta is the OOS-logic fix, not the
chunker.** The honest chunking-track read: semantic ≡ structural on
retrieval hit; they differ on RAGAS (faithfulness 0.8932 vs 0.8826) and cost
(64-min vs 4.6-min index builds).

## Per-type breakdown (content metrics, fixed OOS logic)

| Type | N | hit_id | hit_content | cite_id | cite_content |
|---|---|---|---|---|---|
| lookup | 67 | 0.343 | 0.672 | 0.343 | 0.672 |
| section | 45 | 0.311 | 0.600 | 0.311 | 0.600 |
| synthesis | 9 | 0.222 | **0.667** (6/9, best yet) | 0.222 | 0.667 |
| out_of_scope | 18 | 0.889 | **1.000** (18/18, fix works at scale) | 0.000 (structural) | 0.833 |

- OOS 1.000 is the STEP_009 fix validated at full scale (was 0.000 in exp_003).
- Synthesis 0.667 continues the trend (0.333 → 0.000 → 0.556 → 0.667): wider windows (3000-char MD&A/financial budgets) help cross-section Q's most.
- Section 0.600 trails lookup 0.672 — the 1200-char risk budget may be *too* tight, orphaning section-level answers that span list items.

## Per-ticker (hit_content, worst first)

GS 0.286 (7) · NVDA 0.375 (8) · AMZN 0.444 (9) · WMT 0.500 (8) · MSFT/PFE 0.600 · UNH 0.625 · META 0.667 · JPM 0.714 · AAPL/BAC/GOOGL 0.778 · BRK.B 0.800 · CVX/JNJ/XOM 0.833 · PG 0.857 · TSLA 0.875 · COST 1.000 (2) · **KO 1.000 (6)**.

Two notes: (a) the skew persists but the *order* churned vs exp_003 (GS worst now; KO worst→perfect) — KO's numeric Item 8 answers likely survived intact inside 3000-char table windows; (b) n=5–9 per ticker, so ±1 Q swings rank — read order loosely.

## What this experiment teaches

1. **Budgets buy efficiency, not quality.** 4952 chunks landed in the target band at 1/14th the index time (275s vs 3840s), but context_recall (0.7727) still trails naive (0.8058) and content-hit ties semantic exactly. Document structure alone doesn't beat the baseline on retrieval.
2. **Chunking track verdict after 4/5 chunkers:** naive leads context_recall; semantic leads faithfulness; structural leads content-hit (new era) + efficiency. No chunker dominates — which is itself the finding: the next gains must come from retrieval (hybrid/BM25, Phase 3), not finer chunking. exp_005 late/contextual is now optional, not critical path.
3. **One 429 rate-limit hit** during RAGAS (auto-retried after 4s, run unaffected) — first backpressure seen; nightly full-suite runs should stagger judge calls or lower `ragas_batch_size` if this recurs.
4. No schema changes this step (clean 14-col append). No code changes (runner/chunker frozen since STEP_010/009).

## Run notes

Single attempt, 2718.0s, no kill, no rerun. Per-filing chunk counts deterministic vs smoke (AAPL 141 both). Spend in `data/runtime_costs.jsonl` (gitignored); row cost $0.0327 generation-only.

## Smoke result (6 Q, `--smoke`, kept for the record)

2026-09-07 03:46–03:48 UTC (118.7s): 6 Q / AAPL / 141 chunks, cr=0.80,
fa=1.00, content 0.833 (5/6, OOS True), $0.0016. Source:
`results/smoke/exp_004_structural_20260907_034645/` (user-snapshotted).
Index build 19.0s previewed the full-run 275s.

## Decision for the chunking track

Structural takes `chunking_content` (0.6906). Recommended: **defer exp_005,
start Phase 3 retrieval (BM25/hybrid)** — retrieval-side signals (numbers,
names the dense embedder misses on WMT/AMZN-type filings) are the bigger
lever now, per exp_001's per-ticker analysis.
