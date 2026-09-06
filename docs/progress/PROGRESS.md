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
| STEP_008 | — | — | NEXT: full 139-Q exp_003 run + analysis + leaderboard | TBD | TODO |

## Current headline numbers (frozen)

From `results/experiments.csv` (2 rows):

- `exp_001_naive_baseline`: 139 Q, 20 filings, 4447 chunks, context_recall=0.8058, faithfulness=0.8847, answer_relevancy=0.7428, hit@5=0.6043, cite_acc=0.5612, latency 8731ms, $0.038
- `exp_002_recursive`: 139 Q, 20 filings, 5412 chunks, context_recall=0.7913, faithfulness=0.8595, answer_relevancy=0.7080, hit@5=0.3237 (artifact), cite_acc=0.2158 (artifact), latency 9968ms, $0.0299

Leader: `exp_001` on all RAGAS categories (`results/leaderboard.json`).
Trustworthy cross-chunker signal: content-based same_ticker+section hit@5 = 0.734 (exp_001) vs 0.741 (exp_002) — see `docs/experiments/exp_002_recursive/analysis.md`.

## Data on disk (as of 2026-09-06)

- `data/raw/`: ~50+ 10-K HTML files (AAPL/MSFT/GOOGL have 3-4y; BAC/GS/JPM only 1 filing each — ingest incomplete, see STEP_003).
- `data/eval/qa_pairs.jsonl`: v1 frozen, 139 Q (67 lookup, 45 section, 9 synthesis, 18 OOS), 20 tickers.
- `data/runtime_costs.jsonl`: per-call cost log (all Vertex calls).
- `results/exp_001_naive_baseline/per_question.jsonl` + `results/exp_002_recursive/per_question.jsonl`: per-Q audit trail.
- `results/smoke/exp_003_smoke_metric_test_*`: uncommitted smoke runs proving STEP_006 works.

## Roadmap position

Week 1-2 Foundation: DONE (exp_001 + eval set).
Week 3-4 Chunking: 1/5 full runs done (exp_002) + exp_003 scaffolded + smoke-verified (STEP_007). Full 139-Q exp_003 = STEP_008. Structural/late/contextual TODO.
Week 5-12: NOT STARTED (vectordb, retrieval, RAPTOR, rerank, CRAG, router, cache, API/UI).

## Tracking discipline (locked from STEP_007 onward)

- Every implementation = 1 STEP file + 1 PROGRESS.md row + 1 commit (explicit pathspec, never `git add -A`).
- Never commit: `results/smoke/*` (ephemeral), `data/eval/*.limit*.jsonl` (regenerable), `.claude/scheduled_tasks.lock` (stale), `.env`/`secrets/` (gitignored anyway).
- Canonical ledgers (`results/experiments.csv`, `results/leaderboard.json`, `leaderboard_snapshots/`) change ONLY on full runs + `make leaderboard` — never on smoke.
- Commit command for STEP_007 (run from project root, PowerShell).
  Covers this step ONLY — STEP_006 was closed by `9261360`:

```powershell
git add finrag/chunking.py tests/test_chunking.py `
  docs/progress/PROGRESS.md `
  docs/progress/STEP_007_semantic_chunker_scaffold.md `
  docs/experiments/exp_003_semantic/README.md docs/experiments/exp_003_semantic/config.yaml `
  docs/experiments/exp_003_semantic/analysis.md
git commit -m "STEP_007: semantic chunker + exp_003 scaffold (smoke-verified, hit_at_5_content 0.80)"
```

## How to use this log

1. To recall any step: open its STEP file → it tells you the exact commit, files, verify command.
2. To add a step: copy `_TEMPLATE_STEP.md` → `STEP_007_<name>.md` → fill → link it here.
3. To verify everything still works: `make test`, `make lint`, `make eval-smoke`.
