# exp_050_qdrant — Analysis

**Status:** COMPLETE (STEP_017). Live docker run + `:memory:` preview.
**Sources:** `results/benchmarks/qdrant_docker.json` (canonical, mock, live server, $0), `results/benchmarks/qdrant_preview.json` (`:memory:` preview, STEP_016). Both untracked ephemeral; this file is the record.
**Ledger:** NO `experiments.csv` row (ADR-005: ops benchmark, RAG schema mismatch — all RAGAS columns would be empty). `vectordb` leaderboard category stays null until a locked schema rev adds latency columns (deferred, recorded).

## Canonical numbers — live docker (4447 chunks, 139 questions)

| Metric | InMemory brute-force | Qdrant `:memory:` (preview) | Qdrant docker 1.10.0 (canonical) |
|---|---|---|---|
| p50 query | 1436.2ms | 34.75ms | **11.74ms (~122×)** |
| p95 query | 1952.0ms | 41.78ms | **30.46ms (~64×)** |
| upsert 4447 | — | 6.88s | 8.97s |
| parity top-1 | — | 1.000 | **1.000** |
| parity set overlap | — | 1.000 | **1.000** |

Note: live docker is FASTER than `:memory:` (30.46 vs 41.78ms) — server-side HNSW beats local mode; the preview was not a lower bound after all (recorded correction). Client/server skew noted: qdrant-client 1.19.0 vs server 1.10.0 warns incompatibility but all used calls work.

## Gates (ADR-005): ALL PASS

parity 1.0/1.0 ≥ 0.99 ✓ · p95 30.46ms < 100ms ✓ · $0 marginal (self-hosted) ✓.

## What this means

1. **Qdrant reproduces brute-force ranking exactly at 139/139** — the float32 tail flips from unit tests never appear on real text. Quality-frozen benchmarking validated: no per-DB RAGAS needed.
2. **Production was never shipping brute-force** (~1.4-2.0s/query in Python). Qdrant docker answers in ~12-30ms.
3. Embed 4447 (mock) 6.8s — harness overhead trivial.

## Decision

Qdrant APPROVED as production dense store pending the Weaviate comparison (exp_051, same step): Weaviate must beat 30.46ms p95 convincingly AND clear parity gates to displace it, given Qdrant's exactness.
