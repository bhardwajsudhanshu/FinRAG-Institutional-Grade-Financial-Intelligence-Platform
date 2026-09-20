# STEP_045 — Exact-match ask cache ($0 repeats, 211 tests)

- **Date:** 2026-09-20
- **Git commit:** PENDING (this step)
- **Goal:** Repeat questions cost nothing. No ledger change.
- **Roadmap phase:** Open row → semantic cache, exact-match half (auto-router filed separately)

### 1. Why
Every `/ask` re-ran retrieval + Flash generation even for byte-identical repeats (dashboards poll, users double-click). The cache half of "auto-router/semantic cache" is pure win with zero quality risk; the router half needs eval and stays filed.

### 2. What changed (files — this commit)
- `finrag/cache.py` (new) — `AnswerCache`: key = (strategy, top_k, rerank, case/whitespace-folded question); FIFO eviction at 512 entries; hits/misses stats. No semantic near-matching (stated non-goal).
- `api/main.py` — `/ask` checks cache first (HIT: stored body, `latency_ms=0`, `X-Cache: HIT`); MISS serves normally, stores, `X-Cache: MISS`. Per-worker cache (workers are separate processes); `model_copy` keeps stored bodies immutable.
- `tests/test_cache.py` (new, 10 tests) — normalization, key dimensions, FIFO bound, overwrite, stats, endpoint double-ask (generator called once), variant-hit, top_k-miss.
- `README.md` — generator-refreshed (211 tests) + product row + structure (`cache.py`, X-Cache).
- `docs/progress/STEP_045_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (13 rows), leaderboard, eval set, retrieval math.

### 3. How to verify
```bash
uv run pytest tests/test_cache.py -q  # 10 passed
curl -i -X POST localhost:8000/ask ... # 2nd identical POST -> X-Cache: HIT, latency_ms 0
```

### 4. Result
Full suite: 211 passed, 0 skipped (docker up). Ruff: `finrag/cache.py` + `api/main.py` clean; new test file has only the shared E402 sys.path pattern every sibling test file already carries (STEP_037-recorded convention, untouched).

### 5. How to recall
- STEP file: `docs/progress/STEP_045_ask_cache.md`
- Code: `finrag/cache.py`, `/ask` in `api/main.py`
- Deliberately NOT built: semantic near-match, TTL, cross-worker shared cache (Redis exists in compose — natural home if ever needed), auto-router.

### 6. Next step (STEP_046 candidate)
Only Open items left: hybrid+multiquery/HyDE combos (low priority, ~$ Vertex) or auto-router (strategy selection per question — needs an eval harness first, otherwise it's vibes). Recommend auto-router with a routing eval, or declare the project complete.
