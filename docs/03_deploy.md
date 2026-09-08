# Deploy Guide (STEP_028, refreshed STEP_038)

How to run FinRAG in production (or demo it like production). Assumes
[setup](01_setup.md) is done and Vertex auth works (`make vertex-check`).

## Profiles (pick one)

| Profile | Command | Retrieval | Rerank | Cost/Q | Latency/Q | Needs |
|---|---|---|---|---|---|---|
| Demo | `make serve` + `make ui` | hybrid, in-memory | off | ~$0.0003 | ~9s | Vertex creds |
| Production | `make serve-qdrant` + `make ui` | hybrid, live Qdrant | off | ~$0.0003 | ~8s | + `make docker-up` |
| Flagship | same API, `"rerank": true` (or UI checkbox) | hybrid | Flash pointwise | ~$0.0012 | ~42s | Vertex creds |

Quality behind each profile: demo/production = exp_021 row (content
0.8129); flagship = exp_030 row (content 0.8849). Don't re-benchmark —
the ledger already did.

## Production checklist

1. **Env**: `.env` with `GCP_PROJECT_ID`, `EMBEDDER_BACKEND=vertex`,
   `GENERATOR_BACKEND=vertex`. Delete any machine-level
   `VECTORDB_BACKEND` (OS env beats `.env` and the old `chroma` value is
   fatal now). `CHUNKER_STRATEGY=naive`, `RETRIEVAL_STRATEGY=hybrid` (the
   serve targets pin these; bare `uvicorn` does not — use the targets).
2. **Infra**: `make docker-up`, verify `docker compose ps` (4 up) and
   Qdrant `:6333/healthz` → 200. Volumes persist data; `docker compose
   down` keeps them, `down -v` wipes (never in prod).
3. **Pre-warm once** (STEP_037): `CHUNKER_STRATEGY=naive
   VECTORDB_BACKEND=qdrant uv run python scripts/build_serve_index.py`
   (~5 min, embeds 4447 chunks into `finrag_eval`).
4. **Serve**: `QDRANT_RECREATE=false make serve-qdrant` (uvicorn :8000 —
   attaches in ~2s instead of re-embedding; single worker is fine since
   boots are cheap now, add `--workers 4` behind real traffic — workers
   share the collection, no per-worker rebuild).
5. **Guard**: schedule `scripts/nightly.ps1` (Task Scheduler, 02:00 daily)
   per [nightly ops](02_nightly_ops.md). Mornings: check
   `results/drift_alerts.jsonl` (empty = quiet) and `logs/nightly.log`.
6. **Costs** (measured, all-in per 139-Q run): hybrid $0.10 · reranked
   $0.17 · nightly guard $0.005 (~$0.15/month) · Vertex Search measured
   once ($0.15 for the session, then torn down — not recommended, see
   exp_052).

## What NOT to do

- Don't serve `rerank=true` as the default (42s/Q) — checkbox/flag only.
- Don't run full rerank on the nightly cadence (weekly at most, manually).
- Don't "fix" metrics by editing `results/experiments.csv` or old
  snapshots — append-only, forever. New information = new row.
- Don't leave a Vertex Search endpoint deployed between sessions.

## Scaling notes (when traffic arrives)

- Retrieval p95 is ~30ms (Qdrant) — headroom is 100× before it matters;
  generation (~5-8s) dominates, so scale generators/GPU quota first.
- Repeat questions: add the Redis semantic cache (roadmap; Redis already
  runs in compose doing nothing — the container is the down payment).
- Multi-instance: share the pre-warmed collection across workers
  (STEP_037: deterministic ids make re-upserts idempotent). Remaining for
  a real fleet: upsert-on-ingest when NEW filings arrive (today a new
  filing means a full rebuild) — filed, not built.
