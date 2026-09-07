# exp_050_qdrant — Analysis

**Status:** PREVIEW COMPLETE (STEP_016). Canonical benchmark run (docker + ledger row) deferred to STEP_017.
**Source:** `results/benchmarks/qdrant_preview.json` (untracked ephemeral, mock, `:memory:`, $0, ~2 min wall).

## Preview numbers (4447 chunks, 139 questions)

| Metric | InMemory brute-force | Qdrant `:memory:` |
|---|---|---|
| p50 query | 1349.7ms | **34.75ms (~39×)** |
| p95 query | 1633.3ms | **41.78ms (~39×)** |
| upsert 4447 | — (in-RAM list) | 6.88s |
| parity top-1 | — | **1.000** |
| parity set overlap (top-5) | — | **1.000** |

## What this means

1. **Parity is perfect at scale** (139/139 top-1, 1.0 set overlap) — the unit-test float32 tail flips never materialize on real text with mock vectors. Same-vectors→same-ranking holds; the benchmark can proceed to latency/ops without quality re-verification per DB (spot-check only).
2. **p95 41.78ms clears ADR-005's 100ms bar in `:memory:`** — documented lower bound (no network/Docker). Docker run will add overhead; same harness, same script.
3. **Why brute-force is so slow:** pure-Python cosine over 4447×768-dim per query (~1.3-1.6s). Production was never going to ship this — the benchmark's job is picking its replacement, and Qdrant HNSW is a 39× answer.
4. Embed 4447 (mock) took 7.2s — harness overhead is trivial; the instrument is ready for docker/Weaviate runs.

## Decision (preview, not final)

Qdrant passes all three gates (parity 1.0/1.0, p95 < 100ms) pending the docker confirmation + Weaviate comparison (STEP_017+, needs Docker Desktop up — user action).
