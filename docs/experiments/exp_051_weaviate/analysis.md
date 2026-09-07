# exp_051_weaviate — Analysis

**Status:** COMPLETE (STEP_017). Live docker run, single attempt.
**Source:** `results/benchmarks/weaviate_docker.json` (untracked ephemeral, mock, $0).
**Ledger:** NO `experiments.csv` row (same ops-benchmark reasoning as exp_050).

## Canonical numbers — live docker (4447 chunks, 139 questions)

| Metric | InMemory brute-force | Weaviate 1.27.7 docker | Qdrant docker (exp_050) |
|---|---|---|---|
| p50 query | 1560.2ms | **5.69ms** | 11.74ms |
| p95 query | 2116.9ms | **9.71ms** | 30.46ms |
| upsert 4447 | — | 6.94s | 8.97s |
| parity top-1 | — | 0.9496 (132/139) | 1.000 |
| parity set overlap | — | 0.9468 | 1.000 |

## Verdict: faster, but FAILS parity gates — Qdrant stands

Weaviate is ~3× faster than Qdrant docker (9.71 vs 30.46ms p95) and both
clear the 100ms bar comfortably — but parity 0.9496/0.9468 misses the
locked ≥0.99 gates. 7/139 top-1 flips and ~5% set divergence from
approximate HNSW at default `ef`, on the same vectors Qdrant reproduces
exactly. Per ADR-005's displacement rule (clearly faster AND parity
green), Weaviate does NOT displace Qdrant today.

Follow-up lever (not this step): raise Weaviate query-time `ef` and
re-run the same harness — if parity closes to ≥0.99 while p95 stays well
under Qdrant's 30.46ms, the decision re-opens. Until then: **production
dense store = Qdrant** (exact, 30ms p95, self-hosted, $0 marginal).

## Infra notes (the run also fixed the stack)

Getting here required three compose fixes, all in this step's commit:
1. `ENABLE_MODULES` named text2vec-transformers with no inference endpoint → fatal crash-loop at boot.
2. Client 4.23 refuses server < 1.27.0 → image pinned 1.25.5 → 1.27.7.
3. v4 client needs gRPC :50051 — port mapping added.
Plus one volume wipe (poisoned raft state from crash-loop era) and one
version-skew wipe (1.25.5 raft data under 1.27.7 binary). `make docker-up`
is now verified working from scratch for Qdrant/Weaviate/Redis/Postgres.
