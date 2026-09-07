# exp_050_qdrant

## Hypothesis

With retrieval quality frozen (hybrid sweeps), the vector store is a
latency/ops decision, not a quality decision — IF parity holds (same
vectors → same top-5). Qdrant HNSW should beat brute-force Python cosine
by 10×+ on 4447×768-dim vectors while reproducing its ranking, clearing
ADR-005's p95 < 100ms bar even in `:memory:` mode (documented lower
bound; docker numbers follow when the daemon is up, same harness).

## Setup

- **Store**: Qdrant `:memory:` (`QdrantBackend`, `finrag/vectordb/`)
- **Vectors**: 4447 naive chunks (same set as exp_001/020/021)
- **Queries**: all 139 eval questions (texts only — no generation, no RAGAS, $0)
- **Harness**: `scripts/benchmark_vectordb.py` (mock embeddings — latency/parity don't depend on provenance)
- Baseline: `InMemoryIndex` brute-force in the same process.

## What changes vs. everything before

Nothing qualitative — this is the first experiment that scores
operations instead of answers. No `experiments.csv` row for interface
work; the benchmark row lands with the canonical run (STEP_017).

## Evaluation

Preview (STEP_016, mock, `:memory:`, $0, ~2 min):

```bash
EMBEDDER_BACKEND=mock uv run python scripts/benchmark_vectordb.py --out results/benchmarks/qdrant_preview.json
```

Live docker (needs Docker Desktop up — STEP_017):

```bash
EMBEDDER_BACKEND=mock uv run python scripts/benchmark_vectordb.py --qdrant-url http://localhost:6333 --out results/benchmarks/qdrant_docker.json
```

Decision metrics: parity_top1_rate ≥ 0.99, parity_set_overlap_mean ≥ 0.99, p95 < 100ms.
