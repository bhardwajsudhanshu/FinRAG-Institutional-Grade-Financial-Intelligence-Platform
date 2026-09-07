# exp_051_weaviate

## Hypothesis

Weaviate (HNSW, BYO vectors) matches Qdrant on parity (≥0.99) at
competitive latency. If its p95 beats Qdrant docker's 30.46ms
convincingly with parity intact, it displaces Qdrant; otherwise Qdrant's
exactness wins (ADR-005 criteria, exp_050 decision).

## Setup

- **Store**: Weaviate 1.27.7 docker (`WeaviateBackend`, `finrag/vectordb/`), collection `FinragBenchLive`, `vector_config=self_provided` (no modules, no model download)
- **Vectors**: same 4447 naive chunks, mock embeddings ($0)
- **Queries**: same 139 eval question texts, top-5
- **Harness**: `scripts/benchmark_vectordb.py --backend weaviate` (same instrument as exp_050)

## What changes vs. exp_050

Only the store (and client library). Vectors, chunks, questions, harness identical — pure store effect.
