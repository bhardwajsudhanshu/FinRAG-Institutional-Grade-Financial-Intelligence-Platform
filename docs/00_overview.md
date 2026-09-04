# FinRAG — Overview

## The problem

Financial documents — 10-Ks, 10-Qs, earnings call transcripts — are dense, structured, and full of cross-references. A single missed clause on "geopolitical risk" or "inventory write-down" can cost millions of dollars. Existing financial data tools are great for *numeric* queries (Yahoo Finance, Bloomberg) but bad at *qualitative* ones: "What did Apple say about supply-chain risk in their FY2023 10-K compared to FY2022?" "Did JPMorgan change their position on cryptocurrency exposure quarter-over-quarter?"

FinRAG is a production-grade Retrieval-Augmented Generation (RAG) system that answers these questions with **citations** to the exact source filing and section.

## What FinRAG does

Given a natural-language question, FinRAG:

1. **Retrieves** the most relevant passages from a curated corpus of SEC 10-K filings, with metadata filters by ticker and year
2. **Re-ranks** those passages (in later phases) to put the most relevant first
3. **Generates** a cited answer using Google's Gemini 2.5 family on Vertex AI
4. **Logs** every retrieval, citation, token count, and dollar cost so the system is auditable

## Why this is a hard problem (and a good RAG benchmark)

- **Long, structured documents**: a single 10-K is 80K–200K tokens. Naive chunking loses cross-section context.
- **High recall is critical**: missing one clause is a real loss. We measure Hit@5 and Context Recall strictly.
- **Numeric reasoning**: "What was the year-over-year change in gross margin?" requires the LLM to do math on retrieved numbers, not just paraphrase.
- **Multi-document questions**: "Compare capex between Apple and Microsoft in FY2023" needs retrieval across two corpora.
- **Domain language**: SEC filings use specific legal language ("material adverse effect", "going concern"). A general embedder misses this.

## What this project delivers

A **12-week** build that goes from a naive baseline (`exp_001`) to a production-grade system with:

- 5 chunking strategies compared (recursive, semantic, structural, late chunking, contextual retrieval)
- 4 vector databases benchmarked (ChromaDB, Qdrant, Weaviate, Vertex AI Vector Search)
- 6+ retrieval strategies (dense, BM25, hybrid RRF, multi-query, parent-doc, HyDE, late-chunking retrieval)
- RAPTOR hierarchical indexing
- Cross-encoder re-ranking
- Corrective RAG (CRAG) with web fallback
- Auto-router that picks the right strategy per query
- Redis semantic cache
- FastAPI + Streamlit demo
- Nightly RAGAS drift monitoring

Every step is recorded as an **experiment folder** in `docs/experiments/` with frozen config, raw results, and an analysis of what we learned. The story of *how we got there* is in `docs/decisions/` (Architecture Decision Records).

## Who this is for

- **Hedge funds and equity research analysts**: a tool they'd actually use daily
- **Portfolio projects**: every technique (RAPTOR, late chunking, contextual retrieval, HyDE, CRAG) is the current SOTA in RAG. Showing you've benchmarked them in production is interview-grade.
- **Blog / content**: the `vector_db_benchmark.csv` and `chunking_leaderboard.csv` are real, publishable comparisons.

## Out of scope (by deliberate choice)

- **GraphRAG / entity-relation extraction** — most financial entities are already structured in XBRL, low ROI for the engineering cost.
- **ColBERT-v2 / token-level retrieval** — interesting but operationally painful.
- **LLMLingua prompt compression** — cost optimization, not a product feature.
- **Multi-modal** (10-K charts/tables) — most financial data is already in the text or in structured tables; we can add later if needed.

See `decisions/` for the full reasoning.
