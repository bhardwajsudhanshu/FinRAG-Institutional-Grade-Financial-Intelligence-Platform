# FinRAG — Institutional-Grade Financial Intelligence Platform

> **Production-grade RAG over SEC 10-K filings: hybrid retrieval + re-ranked, cited answers with an auditable experiment ledger. 12 benchmarked experiments, 175 tests, 0 known failures.**

---

## What it does

Ask a financial question, get a cited answer:

```bash
make serve  # terminal 1 — hybrid retrieval over 20 companies' 10-Ks
make ui     # terminal 2 — dashboard at localhost:8501
```

> "What was Apple's revenue in FY2023?"
> → "Apple's net sales for fiscal year 2023 were $383.3 billion. [AAPL_2025-10-31_item_8::0023]"

Every answer carries chunk-level citations, token counts, and dollar cost. Every design decision carries an experiment folder with frozen config, raw results, and analysis.

## Results (the sweep)

139-Q frozen eval set (v1: 67 lookup, 45 section, 9 synthesis, 18 out-of-scope), RAGAS-judged + content-anchored custom metrics:

| Experiment | Retrieval | context_recall | faithfulness | hit@5_content | citation_acc |
|---|---|---|---|---|---|
| exp_001 naive baseline | dense | 0.8058 | 0.8847 | — | 0.5612 |
| exp_002 recursive chunking | dense | 0.7913 | 0.8595 | — | 0.2158 |
| exp_003 semantic chunking | dense | 0.7562 | 0.8932 | 0.5612 | 0.2302 |
| exp_004 structural chunking | dense | 0.7727 | 0.8826 | 0.6906 | 0.2806 |
| exp_020 BM25 | bm25 | 0.7238 | 0.8604 | 0.7194 | 0.5396 |
| exp_021 hybrid RRF | hybrid | 0.8843 | 0.9063 | 0.8129 | 0.6115 |
| exp_022 hybrid + live Qdrant | hybrid | 0.8760 | 0.8979 | 0.8129 | 0.6115 |
| **exp_030 + Flash re-rank** | hybrid+rerank | **0.9132** | **0.9574** | **0.8849** | **0.7266** |
| exp_031 MiniLM re-rank | hybrid+rerank | 0.8430 | 0.8887 | 0.7698 | 0.5683 |
| exp_041 parent-doc | child→parent | 0.7397 | 0.9233 | 0.6978 | 0.5324 |
| exp_042 hybrid-parent | child-fused | 0.8223 | 0.9190 | 0.8129 | 0.6187 |
| exp_043 multi-query | dense+expansion | 0.8003 | 0.9199 | 0.7194 | 0.5252 |

Headlines: hybrid sweeps dense/BM25 alone; live Qdrant reproduces brute-force **139/139 exactly** at 30ms p95; Flash re-rank closes the recall↔citation gap (+11.5pp citations) but costs $0.17/run — so rerank is ON for leadership, OFF by default; ms-marco MiniLM **hurts** on 10-K language (retired, honestly); parent-doc hierarchy helps dense (+9.4pp) but ties hybrid exactly at 3× cost (retired); multi-query is noise (retired); Vertex Search measured slower than Qdrant at 13× the latency plus billing (not recommended). Full story per experiment in `docs/experiments/`; live table in `results/leaderboard.json`.

## Architecture

```
SEC EDGAR → parse (Item 1/1A/7/7A/8) → naive 512/50 chunks → embed (text-embedding-005)
        ├── dense side:  in-memory (dev) or Qdrant :6333 (prod, parity-proven)
        └── lexical side: BM25 (rank-bm25, free)
                → hybrid RRF k=60 (top-20 + top-20 → top-5)
                → optional Flash pointwise re-rank (top-10 → top-5, best-answer mode)
                → Gemini 2.5 Flash answer with [chunk_id] citations + cost log
Options (measured, retired unless noted): parent-doc hierarchy, child-space hybrid fusion,
Flash-vs-MiniLM rerank, multi-query expansion — see experiments table above.
Eval: frozen 139-Q set → RAGAS + content metrics → results/experiments.csv (append-only)
Ops: nightly drift guard (make nightly-smoke) vs exp_021 baseline · serve via FastAPI · demo via Streamlit
```

## Quickstart

```bash
# 1. Environment (.venv + caches on F: drive)
make env
cp .env.example .env   # mocks work offline; set GCP_PROJECT_ID + backends for Vertex

# 2. Local infra (Qdrant, Weaviate, Redis, Postgres)
make docker-up

# 3. Smoke test: ingest + ask (mock or Vertex per .env)
make ingest-sample
make query Q="What are Apple's main risk factors?"

# 4. Serve + demo (hybrid retrieval; needs Vertex creds)
make serve            # API at localhost:8000 (hybrid over in-memory)
make serve-qdrant     # same, dense side on live Qdrant (needs docker-up)
make ui               # dashboard at localhost:8501 (needs make serve running)
# Best-answer mode: POST {"rerank": true} (or the UI checkbox) — Flash re-ranked flagship

# 4b. Persistent serving (skip the ~5-min re-embed on every boot)
CHUNKER_STRATEGY=naive VECTORDB_BACKEND=qdrant uv run python scripts/build_serve_index.py  # once
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid VECTORDB_BACKEND=qdrant QDRANT_RECREATE=false make serve-qdrant
# ^ attaches to the pre-warmed collection in ~2s instead of re-embedding

# 5. Verify + guard
uv run pytest tests -q          # 182 tests, $0
make nightly-smoke              # 10-Q hybrid guard + drift check vs exp_021 (~$0.005)
```

Two Windows gotchas (both recorded in the build log): delete any machine-level `VECTORDB_BACKEND` env var (OS env beats `.env`), and set `HF_HOME=F:/.hf-cache` before MiniLM runs to keep models off C:.

## Project structure

```
api/                     # FastAPI: health / ask(+rerank flag) / leaderboard
ui/                      # Streamlit dashboard (calls the API)
finrag/
├── chunking.py          # naive / recursive / semantic / structural + dispatch
├── parentdoc.py         # parent-document hierarchy builder
├── multiquery.py        # Flash question expansion + cross-formulation fusion
├── embeddings.py        # mock (offline) / Vertex text-embedding-005
├── retrieval.py         # dense + BM25 + hybrid RRF + strategy dispatch
├── rerank.py            # noop / Flash pointwise / MiniLM cross-encoder
├── vectordb/            # backend ABC + Qdrant + Weaviate (:memory: → docker)
├── generation.py        # mock / Vertex Flash (multi-part safe)
├── eval/                # RAGAS runner + content-anchored metrics
├── data/                # SEC ingest + 10-K section parser
├── cli/                 # ingest / ask / eval CLIs
└── config.py            # everything ambient, everything overridable
docs/
├── 00_overview.md 01_setup.md 02_nightly_ops.md 03_deploy.md
├── decisions/           # ADR-001…006 — the why, before the code
├── experiments/         # exp_001…043 — hypothesis, frozen config, results, analysis
└── progress/            # STEP_001…037 — bit-by-bit build log (start here to recall anything)
results/                 # experiments.csv (append-only) + leaderboard + snapshots + per-Q JSONL
scripts/                 # check_drift.py, nightly.ps1, build_serve_index.py, benchmark_vectordb.py, benchmark_vertex_search.py, vertex auth
tests/                   # 182 unit tests (offline) + eval harness
```

## Roadmap status (honest)

| Phase | Status |
|---|---|
| Foundation (eval set, RAGAS, baseline) | DONE — exp_001 |
| Chunking (recursive/semantic/structural) | DONE — naive still leads recall; late/contextual deferred (no signal needs them) |
| Retrieval (BM25 → hybrid RRF → parent-doc → hybrid-parent → multi-query) | DONE — hybrid sweeps; hierarchy helps (+9.4pp) but ties at 3× cost (retired); expansion is noise (retired) |
| Vector DBs (Qdrant ✓, Weaviate measured, Vertex Search measured) | DONE for serving — Qdrant stands |
| Re-rank (Flash wins, MiniLM retired) | DONE |
| Product (FastAPI + best-answer mode + Streamlit + persistent Qdrant) | DONE — pre-warm once, attach in ~2s |
| Ops (nightly drift guard + deploy guide) | DONE |
| Open | HyDE / hybrid+multiquery combo (low priority), multi-worker fleet, nightly cron activation, auto-router/semantic cache |

## Why these choices?

- [ADR-001: Why SEC filings](docs/decisions/adr_001_topic_choice.md)
- [ADR-002: Why Vertex AI](docs/decisions/adr_002_google_stack.md)
- [ADR-003: Eval methodology](docs/decisions/adr_003_eval_methodology.md)
- [ADR-004: Retrieval direction](docs/decisions/adr_004_retrieval_direction.md)
- [ADR-005: Vector-DB benchmark](docs/decisions/adr_005_vectordb_benchmark.md)
- [ADR-006: Re-rank direction](docs/decisions/adr_006_rerank_direction.md)

New here? Read [`docs/progress/PROGRESS.md`](docs/progress/PROGRESS.md) — the chronological index of all 37 build steps.

---

## License

MIT
