# STEP_046 — Snapshot + auto-router measured (heuristic loses, not wired)

- **Date:** 2026-09-20
- **Git commits:** `87c8a4f` SNAPSHOT first (this step), then the step commit (pending)
- **Goal:** (1) Freeze every artifact for later comparison/reuse. (2) Settle auto-router with a routing eval, not vibes. No ledger change.
- **Roadmap phase:** Open row → auto-router (measured-negative, filed); preservation (user-requested)

### 1. Why
Two user asks in one step: save everything comparable, then route. The router got the project's standard treatment — an offline $0 harness with an oracle bound — and failed the bar like MiniLM/multiquery before it.

### 2. What changed (files)
- SNAPSHOT `87c8a4f` (separate commit): 30 force-added files — all `results/smoke/*` proofs, `results/benchmarks/*`, `data/eval/qa_pairs.limit2.jsonl`, `logs/nightly.log` at the STEP_044 DRIFT-OK run. (~185KB.)
- `results/SNAPSHOTS.md` (new, this commit) — living manifest: SHA256 of ledger/leaderboard/eval set, what's-pinned-where, comparison recipes.
- `finrag/router.py` (new) — `route_question` v1 (oos/item-anchors/short-lookups → bm25, else hybrid) + `score_routing` with oracle bounds. NOT wired into the API (verdict §4).
- `tests/eval/evaluate_router.py` (new) — offline routing eval over frozen per-Q JSONLs. Reports content-metric coverage FIRST (missing ≠ zero), then per-type table, oracle, heuristic vs best-single.
- `tests/test_router.py` (new, 10 tests) — rules + scorer, synthetic tables.
- `README.md` — generator-refreshed (221 tests) + Open row (router verdict).
- `docs/progress/STEP_046_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (13 rows), leaderboard, eval set, retrieval math, `/ask` wiring.

### 3. How to verify
```bash
git show 87c8a4f --stat  # 30 snapshot files
uv run python tests/eval/evaluate_router.py  # $0, prints the verdict table
uv run pytest tests/test_router.py -q  # 10 passed
```

### 4. Result — the verdict table (139 Q, frozen per-Q JSONLs)
- Coverage: dense per-Q content metrics are MISSING (frozen pre-fix rows) — excluded loudly, not zeroed. Verdict set: bm25 vs hybrid only.
- Oracle: hit 0.8705 (+5.8pp over hybrid) — headroom EXISTS but is small.
- Heuristic v1: hit 0.7986 vs hybrid-always 0.8129 (−2 Qs net; only 6/139 routed to bm25). No v2 attempted: chasing 112-vs-113 with n=9 synthesis slices would be overfitting theater.
- Verdict: NOT wired. `router.py` + harness stay as measured infrastructure — rerun the evaluator when a new fully-covered strategy arrives.
- Full suite: 221 passed, 0 skipped. Ruff: new source clean; test/script files carry only the repo's shared E402 sys.path pattern.

### 5. How to recall
- STEP file: `docs/progress/STEP_046_router_measured.md`
- Baseline: `results/SNAPSHOTS.md` + commit `87c8a4f`
- Router: `finrag/router.py`, harness `tests/eval/evaluate_router.py`

### 6. Next step (STEP_047 candidate)
One Open item left: hybrid+multiquery/HyDE combos (low priority, ~$ Vertex) — or declare complete. The router harness doubles as its evaluator if combos ever run.
