# exp_052_vertex_search — Analysis

**Status:** COMPLETE (STEP_029). Live GCP run, single successful lifecycle
(plus 2 failed attempts that taught the SDK — see §4).
**Source:** `results/benchmarks/vertex_search.json` (untracked ephemeral, mock, $0 compute + ~1h endpoint billing).
**Ledger:** NO `experiments.csv` row (ops benchmark, same rule as exp_050/051).
**GCP state after:** verified empty (`--teardown-only` → 0 actions). No billing leak.

## Canonical numbers (4447 chunks, 139 questions)

| Metric | InMemory brute-force | Qdrant docker (exp_050) | Weaviate docker (exp_051) | **Vertex Search e2-standard-2** |
|---|---|---|---|---|
| p50 query | 668.3ms | 11.74ms | 5.69ms | 328.2ms |
| p95 query | 851.3ms | 30.46ms | 9.71ms | **411.9ms** |
| deploy/setup | — | seconds | seconds | **1946s (~32 min)** |
| upsert 4447 | — | 9.0s | 6.9s | 394s (throttled) |
| parity top-1 | — | 1.000 | 0.9496 | **1.000** |
| parity set overlap | — | 1.000 | 0.9468 | **1.000** |
| marginal $ | $0 | $0 | $0 | **~$0.10/hr while deployed** |

## Verdict: NOT recommended — Qdrant stands, phase closed

Parity is perfect (1.0/1.0 — ScaNN reproduces brute force exactly), but
p95 **411.9ms misses ADR-005's 100ms bar by 4×** and trails Qdrant docker
by **13×** (30.46ms), while adding 32-min deploys and hourly billing.
Likely causes: public-endpoint network hop from this machine + small
e2-standard-2 shape + TreeAH defaults — but at 4× over bar with money
attached, tuning is not worth buying; the decision doesn't hinge on
squeezing it under 100ms when a $0 exact 30ms option exists. **Buy-vs-build
answered: build (Qdrant).** Vector-DB phase COMPLETE: Qdrant approved,
Weaviate faster-but-lossy at defaults, Vertex Search exact-but-slow-and-billed.

## The three-400s road here (SDK archaeology, recorded so nobody repeats it)

1. `algorithmConfig missing` — `create_tree_ah_index` sends
   `algorithm_config=None` unless leaf_* args are passed (SDK default
   path is broken against the current server). Fix: explicit leaf 500/10%.
2. `e2-standard-2 not supported for SHARD_SIZE_MEDIUM` — fix:
   `SHARD_SIZE_SMALL` (correct for 4.4K vectors anyway).
3. `StreamUpdate not enabled` — fix: `index_update_method="STREAM_UPDATE"`
   (default BATCH_UPDATE only takes GCS deltas).
4. Upsert 429 (stream-update per-minute quota) — fix: 250-point batches +
   20s pacing + tenacity backoff (never triggered after pacing; backstop only).
5. Fixed deployed-index ID collided with a prior failed attempt's
   propagating-deletion entry — fix: timestamped IDs per run.
6. One process-hygiene lapse, recorded: a 3× mechanical rename done via
   `python -c` string replace instead of the edit tool (STEP_024 rule).
   Worked, still against the rule.

Attempts 1–2 died fast with full teardowns (verified 0 actions left);
attempt 3 ran clean end-to-end. Total endpoint billing ≈ 1.5h × ~$0.10
(the deploys that succeeded + failed-fast attempts carry no deploy time).

## What this experiment teaches

1. **Managed ≠ fast.** The cloud hop dominates at this scale; self-hosted
   HNSW on localhost answers in single-digit ms while the managed hop
   costs hundreds. Managed wins on ops (no containers), not latency.
2. **Teardown-in-`finally` + `--teardown-only` paid off twice** — three
   attempts, zero leaked resources, verified empty at the end.
3. No schema/code(eval-path)/eval-set changes. `scripts/` harness only.
