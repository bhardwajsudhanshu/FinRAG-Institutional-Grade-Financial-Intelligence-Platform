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
| STEP_008 | 2026-09-07 | PENDING (commit next) | exp_003 full 139-Q run (6858 chunks, fa=0.8932 track-best) + CSV 14-col migration + leaderboard refresh | `docs/progress/STEP_008_exp003_full_run.md` | PENDING — ready to commit |
| STEP_009 | — | — | NEXT: OOS placeholder-span matcher fix and/or exp_004 structural | TBD | TODO |

## Current headline numbers (frozen)

From `results/experiments.csv` (3 rows, 14-col schema since STEP_008):

- `exp_001_naive_baseline`: 139 Q, 20 filings, 4447 chunks, context_recall=0.8058, faithfulness=0.8847, answer_relevancy=0.7428, hit@5=0.6043, cite_acc=0.5612, latency 8731ms, $0.038 (content cols empty — frozen before fix)
- `exp_002_recursive`: 139 Q, 20 filings, 5412 chunks, context_recall=0.7913, faithfulness=0.8595, answer_relevancy=0.7080, hit@5=0.3237 (artifact), cite_acc=0.2158 (artifact), latency 9968ms, $0.0299 (content cols empty — frozen)
- `exp_003_semantic`: 139 Q, 20 filings, 6858 chunks, context_recall=0.7562, faithfulness=**0.8932 (best)**, answer_relevancy=0.7103, hit@5=0.3237 (artifact), cite_acc=0.2302 (artifact), **hit@5_content=0.5612, cite_content=0.6691**, latency 8862ms, $0.0301

Leaders (`results/leaderboard.json` @ 2026-09-07T00:40:03): chunking/retrieval = exp_001 (context_recall); **chunking_content = exp_003 (0.5612, first holder); end_to_end = exp_003 (faithfulness 0.8932).**
Trustworthy cross-chunker signal: content-based same_ticker+section hit@5 = 0.734 (exp_001) vs 0.741 (exp_002) — see `docs/experiments/exp_002_recursive/analysis.md`.

## Data on disk (as of 2026-09-07)

- `data/raw/`: ~50+ 10-K HTML files (AAPL/MSFT/GOOGL have 3-4y; BAC/GS/JPM only 1 filing each — ingest incomplete, see STEP_003).
- `data/eval/qa_pairs.jsonl`: v1 frozen, 139 Q (67 lookup, 45 section, 9 synthesis, 18 OOS), 20 tickers.
- `data/runtime_costs.jsonl`: per-call cost log (all Vertex calls, incl. both STEP_008 attempts).
- `results/exp_001_naive_baseline/`, `exp_002_recursive/`, `exp_003_semantic/per_question.jsonl`: per-Q audit trail (139 rows each).
- `results/smoke/*`: ephemeral by default (never in STEP commits). Exception, recorded honestly: the user snapshotted smoke outputs inside `9261360` (exp_003_smoke_metric_test_* metric-fix proofs) and `5bd0283` (STEP_007 semantic smoke) — commit message says "changed code in chunking" but stat shows smoke files only, no code. So those smokes are tracked; future smokes stay untracked unless explicitly snapshotted.

## Roadmap position

Week 1-2 Foundation: DONE (exp_001 + eval set).
Week 3-4 Chunking: 2/5 full runs done (exp_002, exp_003). Structural/late/contextual TODO — exp_004 next (section-aware budgets, per exp_003 decision).
Week 5-12: NOT STARTED (vectordb, retrieval, RAPTOR, rerank, CRAG, router, cache, API/UI).

## Tracking discipline (locked from STEP_007 onward)

- Every implementation = 1 STEP file + 1 PROGRESS.md row + 1 commit (explicit pathspec, never `git add -A`).
- Never commit: `results/smoke/*` (ephemeral), `data/eval/*.limit*.jsonl` (regenerable), `.claude/scheduled_tasks.lock` (stale), `.env`/`secrets/` (gitignored anyway).
- Canonical ledgers (`results/experiments.csv`, `results/leaderboard.json`, `leaderboard_snapshots/`) change ONLY on full runs + `make leaderboard` — never on smoke.
- Commit command for STEP_008 (run from project root, PowerShell):

```powershell
git add results/experiments.csv results/leaderboard.json `
  results/leaderboard_snapshots/leaderboard_20260907_004003.json `
  results/exp_003_semantic/per_question.jsonl `
  docs/experiments/exp_003_semantic/analysis.md `
  docs/progress/PROGRESS.md `
  docs/progress/STEP_008_exp003_full_run.md
git commit -m "STEP_008: exp_003 full run (fa=0.8932 best) + CSV 14-col migration + leaderboard refresh"
```

## How to use this log

1. To recall any step: open its STEP file → it tells you the exact commit, files, verify command.
2. To add a step: copy `_TEMPLATE_STEP.md` → `STEP_XXX_<name>.md` → fill → link it here.
3. To verify everything still works: `make test`, `make lint`, `make eval-smoke`.
