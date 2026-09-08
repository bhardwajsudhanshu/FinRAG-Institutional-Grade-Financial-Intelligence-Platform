# exp_052_vertex_search

## Hypothesis

Managed Vector Search trades ops burden for money and (hopefully)
latency: parity should hold (same vectors, ScaNN ANN) with p95 under
ADR-005's 100ms bar, justifying ~$0.10/hr endpoint billing for teams
that won't run Docker. If p95 misses badly, self-hosted Qdrant wins
outright and this experiment is the receipt.

## Setup

- **Store**: Vertex AI Vector Search, Tree-AH index (dim 768,
  DOT_PRODUCT_DISTANCE, leaf 500 / 10%, SHARD_SIZE_SMALL, STREAM_UPDATE),
  e2-standard-2 endpoint, deployed → benchmarked → torn down same session
- **Vectors**: same 4447 naive chunks, mock embeddings ($0 compute)
- **Queries**: same 139 eval question texts, top-5
- **Harness**: `scripts/benchmark_vertex_search.py` (teardown in
  `finally` + `--teardown-only` escape hatch)

## What changes vs. exp_050/051

Only the store (and who operates it). Same vectors/chunks/questions/
parity methodology — pure buy-vs-build data point.
