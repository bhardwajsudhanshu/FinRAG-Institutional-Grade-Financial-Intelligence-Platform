# Deploy Guide (STEP_028)

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
3. **Serve**: `make serve-qdrant` (uvicorn :8000, single worker — add
   `--workers 4` behind real traffic; the index rebuilds per worker, ~5
   min each on Vertex embeddings, so prefer 1 worker + bigger box, or a
   shared Qdrant collection which is already the design).
4. **Guard**: schedule `scripts/nightly.ps1` (Task Scheduler, 02:00 daily)
   per [nightly ops](02_nightly_ops.md). Mornings: check
   `results/drift_alerts.jsonl` (empty = quiet) and `logs/nightly.log`.
5. **Costs** (measured, all-in per 139-Q run): hybrid $0.10 · reranked
   $0.17 · nightly guard $0.005 (~$0.15/month) · Vertex Search NOT
   deployed (would add ~$0.10/hr while the endpoint lives — deploy,
   benchmark, teardown same-day when its turn comes).

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
- Multi-instance: move Qdrant collection out of per-process recreate
  (`finrag_eval` is rebuilt per run today — fine for evals/demos, needs a
  persistent collection + upsert-on-ingest path for a real fleet; filed,
  not built).
