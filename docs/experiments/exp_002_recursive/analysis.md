# exp_002_recursive — Analysis

**Status: pending** (run launched 2026-09-05; will fill in numbers when it lands)

## TL;DR

Hypothesis: paragraph-aware recursive chunking improves `context_recall` and `hit_at_5` over the fixed-size naive baseline (exp_001) because answer-bearing paragraphs are less likely to be split across chunks.

## Setup

- **Chunker**: `recursive_character` (2000 chars, 200 overlap, separators `["\n\n", "\n", ". ", " ", ""]`)
- **Embedding**: `text-embedding-005` (768-dim), Vertex AI
- **Retriever**: in-memory cosine, top-5
- **Generator**: `gemini-2.5-flash`, temperature 0.0
- **Eval set**: v1 (139 Q's, 20 tickers) — identical to exp_001

## Results (filled in post-run)

| Metric | exp_001 (naive) | exp_002 (recursive) | Δ | Direction |
|---|---|---|---|---|
| context_recall | 0.8058 | TBD | TBD | TBD |
| faithfulness | 0.8847 | TBD | TBD | TBD |
| answer_relevancy | 0.7428 | TBD | TBD | TBD |
| hit_at_5 | 0.6043 | TBD | TBD | TBD |
| citation_accuracy | 0.5612 | TBD | TBD | TBD |
| mean_latency_ms | 8731.8 | TBD | TBD | TBD |
| total_cost_usd | $0.0381 | TBD | TBD | TBD |
| n_chunks | 4447 | TBD | TBD | TBD |

## Per-type breakdown (filled in post-run)

| Type | n | exp_001 hit@5 | exp_002 hit@5 | Why |
|---|---|---|---|---|
| lookup | 67 | TBD | TBD | TBD |
| section | 45 | TBD | TBD | TBD |
| synthesis | 9 | TBD | TBD | TBD |
| out_of_scope | 18 | TBD | TBD | TBD |

## Why results improved / regressed (filled in post-run)

Placeholder — once results are in, I'll explain each delta in 2-3 sentences grounded in the per-Q data and the chunker behavior.

## Notes on the comparison

- Both runs use the same eval set, same Q&A, same embedder, same retriever, same generator. The only thing that changed is the chunker.
- The Q&A set was fingerprinted as v1 (sha256=`2dced63fbd22`); see `data/eval/qa_pairs.v1.jsonl.header`.
- Per-Q details for this run: `results/exp_002_recursive/per_question.jsonl` (incremental write, survives crashes).
- Leaderboard snapshot for this run: `results/leaderboard_snapshots/leaderboard_<ts>.json` (written by `make leaderboard` after the run).
