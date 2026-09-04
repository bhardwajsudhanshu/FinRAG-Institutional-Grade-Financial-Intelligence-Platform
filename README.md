# FinRAG — Institutional-Grade Financial Intelligence Platform

> **A production-grade Retrieval-Augmented Generation (RAG) system over SEC 10-K/10-Q filings, designed for sub-second financial question answering with citations.**

---

## Why this exists

Financial documents — 10-Ks, 10-Qs, earnings call transcripts — are dense, structured, and full of cross-references. A single missed clause on "geopolitical risk" or "inventory write-down" can cost millions. FinRAG is built to:

- **Index** 20 companies × 3 years of SEC filings (~200 documents, ~100K chunks)
- **Retrieve** the exact clauses that answer a financial question, with metadata filters by ticker and year
- **Generate** cited answers using Google's Gemini 2.5 family on Vertex AI
- **Benchmark** every component — chunking strategies, vector databases, retrieval pipelines — against a 200-question eval set with RAGAS

It's a 12-week project that goes from a naive baseline to an auto-routed, re-ranked, semantically-cached production system. Every experiment is recorded in `docs/experiments/` so the design decisions are auditable and explainable.

---

## Quickstart

```bash
# 1. Set up the environment (creates .venv on F: drive, redirects uv cache to F:)
make env

# 2. Copy and edit environment config (use mocks until you wire Vertex)
cp .env.example .env

# 3. Start local infrastructure (Qdrant, Weaviate, Redis, Postgres)
make docker-up

# 4. Ingest one sample filing (Apple 10-K FY2023) and run the smoke test
make ingest-sample
make query Q="What are Apple's main risk factors?"
```

Expected output:
```
Answer: Apple Inc. identifies the following principal risk factors: ...
[1] AAPL_10K_2023_Item1A (cosine=0.72)
[2] AAPL_10K_2023_Item1A (cosine=0.68)
Tokens: 4,231 in / 312 out. Cost: $0.0021.
```

---

## Project structure

```
finrag/
├── finrag/                 # core package (ingest, chunk, embed, retrieve, generate)
├── docs/                   # documentation, ADRs, experiment records
│   ├── decisions/          # Architecture Decision Records (the "story")
│   └── experiments/        # one folder per experiment — hypothesis, config, results, analysis
├── results/                # leaderboard, experiments.csv, RAGAS nightly runs
├── tests/                  # pytest suite + RAGAS eval harness
├── ui/                     # Streamlit dashboard
├── api/                    # FastAPI service
├── docker-compose.yml      # Qdrant, Weaviate, Redis, Postgres
├── pyproject.toml          # deps + uv config (cache on F: drive)
└── Makefile                # common commands
```

---

## The 12-week roadmap

| Week | Phase | What we build |
|------|-------|---------------|
| 1–2 | Foundation | Repo, SEC scraper, naive baseline, 200-Q eval set, RAGAS |
| 3–4 | Chunking | 5 strategies: recursive, semantic, structural, late, contextual |
| 5–6 | Vector DBs | ChromaDB vs Qdrant vs Weaviate vs Vertex AI Vector Search |
| 7–8 | Retrieval | Dense, BM25, hybrid RRF, multi-query, parent-doc, HyDE, late-chunking |
| 9 | Indexing | RAPTOR hierarchical trees |
| 10 | Post-retrieval | Cross-encoder rerank, sentence-window, CRAG with web fallback |
| 11 | Product | Auto-router, Redis semantic cache, FastAPI |
| 12 | Polish | Streamlit dashboard, README, deploy guide |

Every week produces **at least one new experiment folder** with frozen config, raw results, and analysis. The "story" of how we got from naive baseline to production is the `docs/decisions/` ADRs.

---

## Why these choices?

See `docs/decisions/`:
- [ADR-001: Why SEC filings](docs/decisions/adr_001_topic_choice.md)
- [ADR-002: Why Vertex AI](docs/decisions/adr_002_google_stack.md)
- ADR-003, 004, 005… written as we make the choices, with data

---

## License

MIT
