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
> 5. Push state is tracked below from STEP_017 onward (STEP_001–016 verified pushed).

## Sync status (tracked from STEP_017 onward)

- Pushed through: `2a1e847` (STEP_016 index DONE) — STEP_001–016 all on `origin/main`, verified 2026-09-07 (`git rev-list --count origin/main..HEAD` baseline).
- Push state: pushed through `2a1e847` (STEP_016). Everything after that is unpushed — verify live with `git log origin/main..HEAD --oneline` (this line is updated on pushes, and may lag the newest index micro-commit by one; the git command is always truth).
- Rule: after every push, update this section (move the boundary). After every STEP commit, the new commit(s) join Unpushed until pushed.

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
| STEP_013 | 2026-09-07 | `3d926e6` exp_020 full run | exp_020 full 139-Q BM25 run (4447 chunks, content-hit leader 0.7194, recall trailer 0.7238) + leaderboard refresh | `docs/progress/STEP_013_exp020_full_run.md` | DONE |
| STEP_014 | 2026-09-07 | `6b536d8` gen fix + hybrid scaffold | Multi-part generation fix (6 tests) + exp_021 hybrid scaffold, smoke 0.833 | `docs/progress/STEP_014_gen_fix_hybrid_scaffold.md` | DONE |
| STEP_015 | 2026-09-07 | `f254df4` exp_021 full run | exp_021 full 139-Q hybrid run (SWEEP all 4 categories: cr 0.8843, content 0.8129) + leaderboard refresh | `docs/progress/STEP_015_exp021_full_run.md` | DONE |
| STEP_016 | 2026-09-07 | `3f59594` ADR-005 + vectordb | Vector-DB phase: ADR-005 + backend interface + Qdrant :memory: (parity 1.0, p95 41.8ms ~39×) + harness + exp_050 | `docs/progress/STEP_016_vectordb_interface_qdrant.md` | DONE |
| STEP_017 | 2026-09-07 | `55416b9` live docker benchmarks | Live docker: Qdrant canonical (p95 30.5ms, parity 1.0, APPROVED) + Weaviate impl (p95 9.7ms but parity 0.95 FAIL) + 3 compose fixes | `docs/progress/STEP_017_live_docker_benchmarks.md` | DONE |
| STEP_018 | 2026-09-07 | `0a32737` Qdrant in eval path | Qdrant in eval path (`vectordb_backend` + adapter + exp_022 scaffold), smoke hybrid+Qdrant 0.833, live .env fixed | `docs/progress/STEP_018_qdrant_in_runner.md` | DONE |
| STEP_019 | 2026-09-07 | `66e48ef` exp_022 full run | exp_022 full 139-Q hybrid+Qdrant run (139/139 identical sets, metrics identical, -1.1s/Q) + batching fix | `docs/progress/STEP_019_exp022_full_run.md` | DONE |
| STEP_020 | 2026-09-07 | `c8d8051` FastAPI serving | FastAPI serving (health/ask/leaderboard, 8 tests, make serve) + optional-embedder threading + machine-env finding | `docs/progress/STEP_020_fastapi_serving.md` | DONE |
| STEP_021 | 2026-09-07 | `305c196` Streamlit demo | Streamlit demo on API (ask + citations + health + leaderboard, 10 tests) | `docs/progress/STEP_021_streamlit_demo.md` | DONE |
| STEP_022 | 2026-09-07 | `6f0d873` ADR-006 + rerank | Rerank phase: ADR-006 + Flash pointwise scorer + runner wiring + exp_030 scaffold, smoke 0.833 | `docs/progress/STEP_022_rerank_flash_pointwise.md` | DONE |
| STEP_023 | 2026-09-07 | `1e6d787` exp_030 full run | exp_030 full 139-Q rerank run (gap closed: cite 0.61->0.73, 5/5 sweep, $0.171 all-in) + reranker category defined | `docs/progress/STEP_023_exp030_full_run.md` | DONE |
| STEP_024 | 2026-09-07 | `7716c59` MiniLM challenger | MiniLM cross-encoder challenger (torch CPU, 4 tests) + exp_031 scaffold, smoke 0.833 in ~half Flash time | `docs/progress/STEP_024_minilm_challenger.md` | DONE |
| STEP_025 | 2026-09-07 | `d1d694b` exp_031 full run | exp_031 full 139-Q run (challenger LOSES: 0.770 < hybrid 0.813, MiniLM retired, phase closed) | `docs/progress/STEP_025_exp031_full_run.md` | DONE |
| STEP_026 | 2026-09-07 | `ef874f8` API best-answer | API best-answer mode (rerank flag + UI checkbox, 3 tests) — cheap default + flagship per request | `docs/progress/STEP_026_api_best_answer.md` | DONE |
| STEP_027 | 2026-09-07 | `108f8bf` drift guard | Nightly drift guard (checker + scheduler entry + runbook, 17 tests, live DRIFT-OK) | `docs/progress/STEP_027_nightly_drift_guard.md` | DONE |
| STEP_028 | 2026-09-07 | `08d2b10` deploy polish | Deploy polish (README sweep table + deploy guide + setup fix) | `docs/progress/STEP_028_deploy_polish.md` | DONE |
| STEP_029 | 2026-09-08 | `7a2b447` Vertex Search bench | Vertex Search benchmark (p95 412ms FAIL, Qdrant stands, phase closed, GCP empty) | `docs/progress/STEP_029_vertex_search_benchmark.md` | DONE |
| STEP_030 | 2026-09-08 | `c40077d` parent-doc + exp_041 | Parent-doc retrieval + exp_041 scaffold (parents == exp_001, smoke 6/6 first ever; STEP_030 ≠ exp_030) | `docs/progress/STEP_030_parent_doc_retrieval.md` | DONE |
| STEP_031 | 2026-09-08 | `b68dc58` exp_041 full run | exp_041 full 139-Q run (content 0.698 +9.4pp, faithfulness best non-rerank, hybrid still leads; STEP_031 ≠ exp_031) | `docs/progress/STEP_031_exp041_full_run.md` | DONE |
| STEP_032 | 2026-09-08 | `1d1dd08` hybrid-parent combo | Hybrid+parent combo + exp_042 scaffold (fuse children, parents generate, smoke 6/6) | `docs/progress/STEP_032_hybrid_parent_combo.md` | DONE |
| STEP_033 | 2026-09-08 | `51dc6ac` exp_042 full run | exp_042 full 139-Q run (exact tie 0.8129 with hybrid, hierarchy retires) | `docs/progress/STEP_033_exp042_full_run.md` | DONE |
| STEP_034 | 2026-09-08 | `6149c47` multiquery flag | Multi-query expansion flag + exp_043 scaffold (orthogonal over any strategy, smoke 6/6) | `docs/progress/STEP_034_multi_query_expansion.md` | DONE |
| STEP_035 | 2026-09-08 | `6ff782d` exp_043 full run | exp_043 full 139-Q run (expansion is noise: +4 net, p~0.42, retired) | `docs/progress/STEP_035_exp043_full_run.md` | DONE |
| STEP_036 | 2026-09-08 | `7be64bc` README refresh | README refresh (12-row table, 175 tests, closed phases) | `docs/progress/STEP_036_readme_refresh.md` | DONE |
| STEP_037 | 2026-09-08 | `a457fbf` serving hardening | Serving hardening (persistent Qdrant + attach in 2.5s + pre-warm script, live-verified) | `docs/progress/STEP_037_serving_hardening.md` | DONE |
| STEP_038 | 2026-09-08 | `e9ff27f` README refresh | README + deploy refresh (serving profiles, 12-row table, 182 tests) | `docs/progress/STEP_038_readme_deploy_refresh.md` | DONE |
| STEP_039 | 2026-09-08 | `49a1e03` HyDE + exp_044 | HyDE hypothetical-doc retrieval + exp_044 scaffold (composes with all strategies, smoke 6/6) | `docs/progress/STEP_039_hyde_retrieval.md` | DONE |
| STEP_040 | — | — | NEXT: exp_044 full 139-Q run (~50 min) + verdict vs exp_001 + leaderboard | TBD | TODO |
| STEP_011 | — | — | NEXT: exp_004 full 139-Q run + analysis + leaderboard | TBD | TODO |

## Current headline numbers (frozen)

From `results/experiments.csv` (12 rows, 14-col schema since STEP_008):

- `exp_001_naive_baseline`: 139 Q, 20 filings, 4447 chunks, context_recall=0.8058, faithfulness=0.8847, answer_relevancy=0.7428, hit@5=0.6043, cite_acc=0.5612, latency 8731ms, $0.038 (content cols empty — frozen before fix)
- `exp_002_recursive`: 139 Q, 20 filings, 5412 chunks, context_recall=0.7913, faithfulness=0.8595, answer_relevancy=0.7080, hit@5=0.3237 (artifact), cite_acc=0.2158 (artifact), latency 9968ms, $0.0299 (content cols empty — frozen)
- `exp_003_semantic`: 139 Q, 20 filings, 6858 chunks, context_recall=0.7562, faithfulness=**0.8932 (best)**, answer_relevancy=0.7103, hit@5=0.3237 (artifact), cite_acc=0.2302 (artifact), **hit@5_content=0.5612 (v1 OOS logic; fixed-logic projection 0.6906)**, cite_content=0.6691, latency 8862ms, $0.0301
- `exp_004_structural`: 139 Q, 20 filings, 4952 chunks, context_recall=0.7727, faithfulness=0.8826, answer_relevancy=0.7340, hit@5=0.3957 (artifact), cite_acc=0.2806 (artifact), **hit@5_content=0.6906 (fixed logic; non-OOS 0.645 = exp_003)**, cite_content=0.6691, latency 8908ms, $0.0327
- `exp_020_bm25`: 139 Q, 20 filings, 4447 chunks (= exp_001, pure retrieval effect), context_recall=0.7238, faithfulness=0.8604, answer_relevancy=0.6670, hit@5=**0.6115 (best, valid)**, cite_acc=0.5396, **hit@5_content=0.7194 (best)**, cite_content=**0.7050 (best)**, latency **4374ms (fastest)**, $0.0354
- `exp_021_hybrid_rrf`: 139 Q, 20 filings, 4447 chunks, context_recall=**0.8843 (best, +8pp)**, faithfulness=**0.9063 (best)**, answer_relevancy=**0.7496 (best)**, hit@5=**0.6763 (best)**, cite_acc=**0.6115 (best)**, **hit@5_content=0.8129 (best)**, cite_content=**0.7986 (best)**, latency 8961ms, $0.0366
- `exp_022_hybrid_qdrant`: 139 Q, 20 filings, 4447 chunks, cr=0.8760/fa=0.8979/ar=0.7587 (RAGAS ±noise vs exp_021), customs IDENTICAL (0.6763/0.6115/0.8129/0.7986), **139/139 identical retrieved sets**, latency 7824ms (-1.1s/Q), $0.0365 — parity proof, deployable as-is
- `exp_030_flash_rerank`: 139 Q, 20 filings, 4447 chunks, cr=**0.9132**, fa=**0.9574**, ar=**0.7864**, hit@5=**0.7770** (+10.1pp), cite=**0.7266** (+11.5pp), content **0.8849** (+7.2pp), cite_content **0.8561**, 41966ms/Q, row $0.038 / **all-in $0.1714** — gap closed (RANKING), 5/5 sweep
- `exp_031_minilm_rerank`: 139 Q, 20 filings, 4447 chunks, cr=0.8430/fa=0.8887/ar=0.7027, hit@5=0.6259/cite=0.5683, content **0.7698 (< hybrid — hurts)**, cite_content 0.7554, 9442ms/Q (4.4× Flash), $0 scoring — challenger LOSES, retired (ms-marco ≠ 10-K language)
- `exp_041_parent_doc`: 139 Q, 20 filings, 4447 parents + ~13.2K children, cr=0.7397, fa=**0.9233 (best non-rerank)**, ar=0.6989, hit@5=0.5899/cite=0.5324, content **0.6978 (+9.4pp vs naive)**, cite_content 0.6763, 10239ms/Q, $0.0375 — hierarchy real but small; hybrid leads by 11pp
- `exp_042_hybrid_parent`: 139 Q, 20 filings, 4447 parents + ~13.2K children, cr=0.8223/fa=0.9190/ar=0.7245, hit@5=**0.6835 (best chunk_id)**/cite=**0.6187 (best chunk_id)**, content **0.8129 (EXACT tie hybrid)**/cite_content 0.7842, 10563ms/Q, $0.0366 — partial redemption (fuses cleanly), retired at 3× cost
- `exp_043_multi_query`: 139 Q, 20 filings, 4447 chunks, cr=0.8003/fa=0.9199/ar=0.7317, hit@5=0.5755/cite=0.5252, content 0.7194 (= BM25 exactly, 82/100 overlap), cite_content 0.6978, 25153ms/Q, $0.0378 (+~$0.01 expansion) — expansion is NOISE non-OOS (+4, p~0.42), retired

Leaders (`results/leaderboard.json` @ 2026-09-07T13:02:01): **SWEEP 5/5 — exp_030_flash_rerank leads every decided category** (cr=0.9132; content 0.8849; cite 0.7266; fa=0.9574). Only `vectordb` null (ops track, no latency columns by design).
Trustworthy cross-chunker signal: content-based same_ticker+section hit@5 = 0.734 (exp_001) vs 0.741 (exp_002) — see `docs/experiments/exp_002_recursive/analysis.md`.

## Data on disk (as of 2026-09-07)

- `data/raw/`: ~50+ 10-K HTML files (AAPL/MSFT/GOOGL have 3-4y; BAC/GS/JPM only 1 filing each — ingest incomplete, see STEP_003).
- `data/eval/qa_pairs.jsonl`: v1 frozen, 139 Q (67 lookup, 45 section, 9 synthesis, 18 OOS), 20 tickers.
- `data/runtime_costs.jsonl`: per-call cost log (all Vertex calls, incl. both STEP_008 attempts).
- `results/exp_001_naive_baseline/`, `exp_002_recursive/`, `exp_003_semantic/`, `exp_004_structural/`, `exp_020_bm25/`, `exp_021_hybrid_rrf/`, `exp_022_hybrid_qdrant/`, `exp_030_flash_rerank/`, `exp_031_minilm_rerank/per_question.jsonl`: per-Q audit trail (139 rows each).
- `results/smoke/*` + `results/benchmarks/*` + `data/eval/*.limit*.jsonl`: ephemeral instrument outputs, snapshotted by the user in `9261360` (metric-fix smokes), `5bd0283` (STEP_007 smoke), `b03f4a7` (STEP_009 smoke + limit6 slice) — all three commits are smoke/limit only, no code. New outputs stay untracked until snapshotted (STEP_010's smoke rode along in `d292dfd` because it was user-staged).

## Roadmap position

Week 1-2 Foundation: DONE (exp_001 + eval set).
Week 3-4 Chunking: 3/5 full runs done (exp_002, exp_003, exp_004). No chunker beats naive on context_recall; semantic leads faithfulness; structural leads content-hit + efficiency. exp_005 (late/contextual) DEFERRED per exp_004 decision.
Week 5-8 Retrieval (Phase-3 in-memory COMPLETE STEP_015): hybrid RRF sweeps all 4 categories (cr 0.8843, content 0.8129, fa 0.9063). Production retrieval path = naive chunks + hybrid RRF.
Vector-DB benchmark (STEP_016 opened, STEP_017 decided live, STEP_018-019 wired+proven, STEP_029 closed with managed): **production = Qdrant, phase COMPLETE** (docker p95 30.5ms parity 1.0; Weaviate 9.7ms but parity 0.95 FAIL; Vertex Search 412ms FAIL + billed — all three measured, GCP verified empty; hybrid+Qdrant 139/139 end-to-end parity; no ledger rows for ops benchmarks by rule).
Product surface (STEP_020 API + STEP_021 demo + STEP_026 best-answer + STEP_037 hardening): FastAPI + Streamlit + persistent Qdrant (pre-warm once, attach in ~2s, deterministic ids); 182 tests green (0 skips with Docker up).
Ops (STEP_027 guard + STEP_028 polish): nightly drift guard (`make nightly-smoke` ~$0.005 + checker with noise floor + Task Scheduler entry + runbook) — live DRIFT-OK; README leads with the sweep; deploy guide with 3 measured profiles. Machine-env warning: OS exports `VECTORDB_BACKEND=chroma` (beats `.env` in pydantic-settings; user should delete it — invalid value, crashes non-overridden runs; full-run commands must pin all four vars).
Rerank phase (STEP_022 opened, STEP_023 won, STEP_025 closed): Flash pointwise closes the gap (cite 0.61->0.73, recall 0.88->0.91 too) — 5/5 sweep, all-in $0.171/run. MiniLM challenger LOSES (0.770 < hybrid 0.813 — ms-marco ≠ 10-K language, retired). Rerank ON for leadership, OFF by default for cost.
Retrieval leftovers (STEP_030 opened, STEP_031 measured): parent-doc hierarchy (256-children → 512-parents == exp_001) scores content 0.698 (+9.4pp over direct dense, best non-rerank faithfulness 0.9233) but trails hybrid by 11pp at 3× index cost — useful, not leading; hybrid+parent-doc combo filed; STEP_032 built it (smoke 6/6), full run decided: tie at 3x cost, hierarchy retired (STEP_032-033). Question-side multi-query flag live, exp_043 isolates it vs exp_001 (STEP_034) — measured STEP_035: noise (+4, p~0.42), retired. McNemar paired reasoning adopted as standard. Only HyDE + hybrid+multiquery remain filed, low priority.
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
