# FinRAG — Progress Log (master index)

> **Purpose:** one chronological file to recall *every implementation step bit-by-bit*.
> If you come back in 1 month, start here, then open the linked STEP file,
> ADR, experiment folder, and git commit.
>
> **Rules (locked):**
> 1. One STEP file per implementation (never edit an old STEP — append a new one).
> 2. Every STEP links: git commit + files changed + ADR/exp + how to verify.
> 3. `results/experiments.csv` and `results/leaderboard.json` are append-only ledgers — same rule.
> 4. Uncommitted work is always tracked as `Status: PENDING` until committed.

## Index

| Step | Date | Git commit | What | Recall path | Status |
|------|------|------------|------|-------------|--------|
| STEP_001 | 2026-09-05 | `6cc10d3` Initial commit | Repo scaffold: config, chunk/emb/ret/gen, CLI, docker, ADRs 001-002, exp_001 skeleton | `docs/progress/STEP_001_initial_scaffold.md` | DONE |
| STEP_002 | 2026-09-05 | `a4a94a2` checked with vertex ai | Vertex wiring: real embed/gen, cost tracking, auth script | `docs/progress/STEP_002_vertex_wiring.md` | DONE |
| STEP_003 | 2026-09-05 | `6104e9b` 139 Q eval + accuracy | Full ingest (20 tickers), 139-Q v1 eval set, RAGAS runner, exp_001 baseline run | `docs/progress/STEP_003_eval_set_exp001.md` | DONE |
| STEP_004 | 2026-09-05 | `3b4f77a` Recursive chunking implemented | Recursive chunker + dispatch + chunking tests + exp_002 scaffold | `docs/progress/STEP_004_recursive_chunker_code.md` | DONE |
| STEP_005 | 2026-09-05 | `84a88f5` recursive results | exp_002 full run (5412 chunks) + analysis: chunk_id artifact found | `docs/progress/STEP_005_exp002_results.md` | DONE |
| STEP_006 | 2026-09-06 | `9261360` updated logs | Content-anchored metrics fix: `span_appears_in_chunk`, `hit_at_5_content`, smoke-tested for exp_003 | `docs/progress/STEP_006_content_metrics_fix.md` | DONE |
| STEP_007 | 2026-09-06 | `b0d510e` semantic chunker + exp_003 scaffold | Semantic chunker + exp_003 scaffold, smoke-verified (5 Q: hit@5_content 0.80 vs 0.40) | `docs/progress/STEP_007_semantic_chunker_scaffold.md` | DONE |
| STEP_008 | 2026-09-07 | `c685943` exp_003 full run | exp_003 full 139-Q run (6858 chunks, fa=0.8932 track-best) + CSV 14-col migration + leaderboard refresh | `docs/progress/STEP_008_exp003_full_run.md` | DONE |
| STEP_009 | 2026-09-07 | `86c2329` OOS sentinel fix | OOS sentinel normalization fix (`normalize_source_span`), smoke-verified OOS flip, no ledger change | `docs/progress/STEP_009_oos_sentinel_fix.md` | DONE |
| STEP_010 | 2026-09-07 | `45e699b` structural chunker + exp_004 scaffold | Structural chunker (section budgets) + exp_004 scaffold, smoke 0.833 content, 19s index build | `docs/progress/STEP_010_structural_chunker_scaffold.md` | DONE |
| STEP_011 | 2026-09-07 | `d292dfd` exp_004 full run | exp_004 full 139-Q run (4952 chunks, content 0.6906 = projection, OOS 1.000) + leaderboard refresh (also carried user-staged STEP_010 smoke snapshot) | `docs/progress/STEP_011_exp004_full_run.md` | DONE |
| STEP_012 | 2026-09-07 | `7c2ca42` ADR-004 + BM25/RRF | Phase 3 opens: ADR-004 + BM25/RRF paths + retrieval_strategy + 13 tests + exp_020 scaffold, smoke 0.833 | `docs/progress/STEP_012_phase3_bm25_hybrid.md` | DONE |
| STEP_013 | — | — | NEXT: exp_020 BM25 full 139-Q run + analysis + leaderboard | TBD | TODO |
| STEP_012 | — | — | NEXT: Phase 3 retrieval (BM25 → hybrid RRF); ADR-004 first | TBD | TODO |
| STEP_011 | — | — | NEXT: exp_004 full 139-Q run + analysis + leaderboard | TBD | TODO |

## Current headline numbers (frozen)

From `results/experiments.csv` (4 rows, 14-col schema since STEP_008):

- `exp_001_naive_baseline`: 139 Q, 20 filings, 4447 chunks, context_recall=0.8058, faithfulness=0.8847, answer_relevancy=0.7428, hit@5=0.6043, cite_acc=0.5612, latency 8731ms, $0.038 (content cols empty — frozen before fix)
- `exp_002_recursive`: 139 Q, 20 filings, 5412 chunks, context_recall=0.7913, faithfulness=0.8595, answer_relevancy=0.7080, hit@5=0.3237 (artifact), cite_acc=0.2158 (artifact), latency 9968ms, $0.0299 (content cols empty — frozen)
- `exp_003_semantic`: 139 Q, 20 filings, 6858 chunks, context_recall=0.7562, faithfulness=**0.8932 (best)**, answer_relevancy=0.7103, hit@5=0.3237 (artifact), cite_acc=0.2302 (artifact), **hit@5_content=0.5612 (v1 OOS logic; fixed-logic projection 0.6906)**, cite_content=0.6691, latency 8862ms, $0.0301
- `exp_004_structural`: 139 Q, 20 filings, 4952 chunks, context_recall=0.7727, faithfulness=0.8826, answer_relevancy=0.7340, hit@5=0.3957 (artifact), cite_acc=0.2806 (artifact), **hit@5_content=0.6906 (fixed logic; non-OOS 0.645 = exp_003)**, cite_content=0.6691, latency 8908ms, $0.0327

Leaders (`results/leaderboard.json` @ 2026-09-07T04:54:08): chunking/retrieval = exp_001 (context_recall); **chunking_content = exp_004 (0.6906); end_to_end = exp_003 (faithfulness 0.8932).**
Trustworthy cross-chunker signal: content-based same_ticker+section hit@5 = 0.734 (exp_001) vs 0.741 (exp_002) — see `docs/experiments/exp_002_recursive/analysis.md`.

## Data on disk (as of 2026-09-07)

- `data/raw/`: ~50+ 10-K HTML files (AAPL/MSFT/GOOGL have 3-4y; BAC/GS/JPM only 1 filing each — ingest incomplete, see STEP_003).
- `data/eval/qa_pairs.jsonl`: v1 frozen, 139 Q (67 lookup, 45 section, 9 synthesis, 18 OOS), 20 tickers.
- `data/runtime_costs.jsonl`: per-call cost log (all Vertex calls, incl. both STEP_008 attempts).
- `results/exp_001_naive_baseline/`, `exp_002_recursive/`, `exp_003_semantic/`, `exp_004_structural/per_question.jsonl`: per-Q audit trail (139 rows each).
- `results/smoke/*` + `data/eval/*.limit*.jsonl`: ephemeral proofs, snapshotted by the user in `9261360` (metric-fix smokes), `5bd0283` (STEP_007 smoke), `b03f4a7` (STEP_009 smoke + limit6 slice) — all three commits are smoke/limit only, no code. New smokes stay untracked until snapshotted.

## Roadmap position

Week 1-2 Foundation: DONE (exp_001 + eval set).
Week 3-4 Chunking: 3/5 full runs done (exp_002, exp_003, exp_004). No chunker beats naive on context_recall; semantic leads faithfulness; structural leads content-hit + efficiency. exp_005 (late/contextual) DEFERRED per exp_004 decision.
Week 5-8 Retrieval (OPENED STEP_012): ADR-004 accepted — BM25 ablation (exp_020) then hybrid RRF (exp_021), naive chunks fixed, in-memory only. Retrieval axis live via `retrieval_strategy` setting.
Week 5-12 rest: NOT STARTED (vectordb, RAPTOR, rerank, CRAG, router, cache, API/UI).

## Tracking discipline (locked from STEP_007 onward)

- Every implementation = 1 STEP file + 1 PROGRESS.md row + 1 commit (explicit pathspec, never `git add -A`).
- STEP commits exclude regenerable/ephemeral artifacts (`results/smoke/*`, `data/eval/*.limit*.jsonl`, `.env`/`secrets/`). Settled pattern: the user snapshots notable smoke/limit files in separate commits (`9261360`, `5bd0283`, `b03f4a7` — all three commits are smoke/limit only, no code). New smokes stay untracked until snapshotted (STEP_010's smoke rode along in `d292dfd` because it was user-staged).
- Canonical ledgers (`results/experiments.csv`, `results/leaderboard.json`, `leaderboard_snapshots/`) change ONLY on full runs + `make leaderboard` — never on smoke.
- Commit template for full-run steps (run from project root, PowerShell; list files explicitly — past instances: STEP_008 §7 in its STEP file, STEP_011 §3 in its STEP file):

```powershell
git add results/experiments.csv results/leaderboard.json `
  results/leaderboard_snapshots/leaderboard_<ts>.json `
  results/<exp>/per_question.jsonl `
  docs/experiments/<exp>/analysis.md `
  docs/progress/PROGRESS.md `
  docs/progress/STEP_XXX_<name>.md
git commit -m "STEP_XXX: <one-line result>"
```

## How to use this log

1. To recall any step: open its STEP file → it tells you the exact commit, files, verify command.
2. To add a step: copy `_TEMPLATE_STEP.md` → `STEP_XXX_<name>.md` → fill → link it here.
3. To verify everything still works: `make test`, `make lint`, `make eval-smoke`.
