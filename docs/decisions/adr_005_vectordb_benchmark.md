# ADR-005: Vector-DB Benchmark Direction

**Status:** Accepted
**Date:** 2026-09-07
**Deciders:** Project lead, FinRAG

## Context

Retrieval quality is frozen: hybrid RRF over naive chunks sweeps all four
decided categories (STEP_015). The remaining question is operational, not
qualitative: which vector store serves the dense side at production load,
at what latency and cost? Candidates from `docker-compose.yml`: Qdrant,
Weaviate (self-hosted) + Vertex AI Vector Search (managed, ADR-002).
Environment as of STEP_016: Docker client present but daemon DOWN
(starting Docker Desktop is a user action); `qdrant-client 1.19.0` +
`weaviate-client 4.23.0` installed via `uv sync --extra vectordbs`.

## Decision

1. **Benchmark order: Qdrant → Weaviate → Vertex AI Vector Search.**
   Qdrant first because `qdrant-client` runs fully offline in `:memory:`
   mode (same HNSW engine, no server) — benchmarkable TODAY with zero
   infra. Weaviate needs a live server (Docker). Vertex Search needs GCP
   index deployment (~$0.10/hr while deployed — create, benchmark,
   teardown same-day per `docs/01_setup.md` §4d).
2. **Quality is frozen; measure latency/ops only.** Each DB must reproduce
   in-memory dense top-5 (recall parity ≥ 0.99 on the eval set); the scored
   metrics are p50/p95 query latency, index-build time, and $/1K Q. No new
   RAGAS runs for DB parity (same vectors → same ranking, verified by
   parity check, not judged).
3. **Experiment numbers exp_050/051/052** (`exp_050_qdrant`,
   `exp_051_weaviate`, `exp_052_vertex_search`) — exp_030 was already
   promised to the re-ranker (exp_002 analysis) and exp_040 to RAPTOR.
4. **Interface first:** `finrag/vectordb/` backend ABC (`upsert/query`),
   one implementation per DB, each tested against whatever runs offline.
   The eval runner is NOT rewired yet — DBs enter the pipeline only after
   parity is proven (STEP_017+).
5. **Decision criteria (locked now, applied at STEP_017+ review):** p95 <
   100ms on 4447 chunks for the managed/self-hosted pick; ops burden
   (Docker vs serverless) breaks ties; cost/1K Q recorded in analysis.

## Rationale

- **`:memory:` is representative for Qdrant's algorithmics** (same HNSW)
  minus network/Docker overhead — documented as a lower bound; Docker
  numbers follow when the daemon is up, same harness, same script.
- **Parity-not-quality** keeps the benchmark cheap: no LLM judge, no
  generation — pure vector ops, runnable in minutes on CPU.
- **Vertex Search last** for cost discipline (hourly billing while the
  endpoint lives).

## Consequences

- STEP_016: interface + Qdrant backend tested on `:memory:` + exp_050
  scaffold. Weaviate impl deferred to STEP_017 (needs Docker up — user action).
- A `scripts/benchmark_vectordb.py` harness lands with the first benchmark
  run (STEP_017), not now — interface + parity-test helper first.
- `results/experiments.csv` gains NO rows for interface work (no full
  eval); exp_050+ rows appear only with benchmark numbers.

## Alternatives considered

- **Docker-first, Qdrant-in-compose:** blocked on the daemon; waiting
  stalls the project. Rejected — `:memory:` unblocks today.
- **ChromaDB (already a dep):** runs in-process already, but nobody asked
  the production question about it; the compose file (project contract)
  names Qdrant/Weaviate/Vertex. Chroma stays the dev default, out of the
  benchmark.
- **Benchmarking generation end-to-end per DB:** wasteful — same vectors
  give same contexts give same answers; parity check suffices.

## References

- `docker-compose.yml` (the infra contract), `docs/01_setup.md` §4d/§5
- STEP_015 sweep (`docs/experiments/exp_021_hybrid_rrf/analysis.md`)
