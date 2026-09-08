# STEP_037 — Serving hardening (persistent Qdrant + fast restarts)

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** Boots stop re-embedding 4447 chunks; pre-warm once, attach forever. No ledger change.
- **Roadmap phase:** Serving hardening (from deploy notes + STEP_028 follow-ups)

### 1. Why
Every boot (API lifespan, eval run, nightly) re-embedded the full corpus
(~5 min Vertex + upsert) because the collection was recreated per run.
For serving that means slow restarts and wasted spend; for multi-worker
uvicorn it would mean N parallel rebuilds. Persistent collection +
attach-if-populated fixes all three.

### 2. What changed (files — this commit)
- `finrag/vectordb/qdrant_backend.py` — `recreate` flag (True = wipe+create, default = frozen behavior; False = create-if-missing); `point_count()` (server truth, 0 when missing); **deterministic md5(chunk_id) uint64 point ids** (Qdrant takes ints/UUIDs, not strings) so re-upserts are idempotent in ANY order.
- `finrag/config.py` — `qdrant_collection="finrag_eval"`, `qdrant_recreate=True`.
- `finrag/eval/ragas_runner.py` — `_build_dense_index`: recreate=True rebuilds (frozen path); recreate=False + populated collection ATTACHES without embedding; empty/missing builds normally.
- `scripts/build_serve_index.py` — NEW pre-warm entrypoint (fails clearly unless qdrant backend).
- `tests/test_vectordb.py` — `TestPersistence` (recreate-False creates, idempotent re-upsert, recreate-True wipes) + `TestLiveAttach` (true cross-instance attach, skips offline).
- `.env.example` — documented all serving settings incl. previously-undocumented `RERANK_*`/`MULTIQUERY_*`.
- `docs/progress/STEP_037_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (12 rows), leaderboard, eval set, retrieval math.
- NOT committed: `results/smoke/attach_proof_*/` (ephemeral proof).

### 3. How it works
Deploy flow: `VECTORDB_BACKEND=qdrant uv run python scripts/build_serve_index.py` (once, ~5 min) → serve with `QDRANT_RECREATE=false` → lifespan attaches in ~2s. Eval/nightly default (`true`) rebuilds deterministically — frozen behavior untouched.

### 4. How to verify
```bash
uv run pytest tests/test_vectordb.py -q   # 16 pass :memory: (+live attach when docker up)
docker compose up -d qdrant
CHUNKER_STRATEGY=naive VECTORDB_BACKEND=qdrant uv run python scripts/build_serve_index.py
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid RERANK_BACKEND=none VECTORDB_BACKEND=qdrant QDRANT_RECREATE=false uv run python -m finrag.cli.eval --exp attach_proof --limit 2 --smoke
# expect "Attached to Qdrant collection 'finrag_eval' (4447 points, no re-embed)"
```

### 5. Result / numbers
- Unit: 20/20 vectordb live (incl. cross-instance attach) when Docker up; :memory: subset offline. Full suite at commit time (see PROGRESS).
- During-step correction, recorded: first id design (positional `i + server_count`) FAILED its own test — re-upsert duplicated (6 not 3). Deterministic md5 ids fixed it (test now asserts idempotency, not just attach). Tests earning their keep.
- Live proof 2026-09-08 (user started Docker on request): pre-warm 4447 in 318s; attach boot **2.5s (127× faster)**; 2/2 content hits, hybrid+qdrant rows. Ruff: only shared E402 pattern.
- Note: full `docker compose up` (all 4) was already running from the user's `docker up` — Weaviate tests ran live too (no skips this step).

### 6. How to recall
- STEP file: `docs/progress/STEP_037_serving_hardening.md`
- Code: `finrag/vectordb/qdrant_backend.py` (recreate/point_count/ids), `_build_dense_index` attach branch, `scripts/build_serve_index.py`
- Tests: `tests/test_vectordb.py::TestPersistence`, `::TestLiveAttach`
- Proof: `results/smoke/attach_proof_20260908_150318/` (untracked)

### 7. Next step (STEP_038 candidate)
README/deploy refresh with serving profiles (pre-warm + attach flow), or hybrid+multiquery combo (low priority), or HyDE (untested). Recommend README refresh: front door is 9 steps stale and serving now has three documented profiles.
