# ADR-002: Why Google Vertex AI (Gemini + text-embedding-005)

**Status:** Accepted
**Date:** 2026-09-05
**Deciders:** Project lead, FinRAG

## Context

We need to choose an LLM and embedding provider for the project. The
candidates:

| Provider | Models considered | Pricing tier |
|----------|-------------------|--------------|
| OpenAI | gpt-4o, gpt-4o-mini, text-embedding-3-small | Mid |
| Anthropic | claude-sonnet-4, claude-haiku-4 | Mid-high |
| Google Vertex AI | gemini-2.5-pro, gemini-2.5-flash, text-embedding-005 | Low (Flash) to mid (Pro) |
| Local (Ollama) | llama-3.1-8b, mistral-7b | Free but slow |

The user has a GCP account and has used Vertex AI before, so we can move
fast on auth and quota setup.

## Decision

We standardized on **Google Vertex AI** with the following model tiers:

- **Generation (query path)**: `gemini-2.5-flash` (default)
- **Generation (eval Q&A synthesis, hard cases)**: `gemini-2.5-pro`
- **Embeddings**: `text-embedding-005` (768-dim, 2048-token context)
- **Vector DB (one of 4)**: Vertex AI Vector Search (ScaNN-based)

We expose pluggable backends (`finrag/embeddings.py`, `finrag/generation.py`)
so a swap to OpenAI or local models is a 5-line change if needed.

## Rationale

### 1. Cost-efficiency for an iterative project
- Gemini 2.5 Flash input is $0.075/M tokens — 10x cheaper than GPT-4o
- text-embedding-005 is $0.025/M tokens — same as OpenAI's small
- For a 3-month project with hundreds of experiments, this matters
- We log every call's cost in `data/runtime_costs.jsonl` so we always
  know what we're spending

### 2. Long context for RAG
- Gemini 2.5 Flash has a 1M-token context window
- Even Pro has 2M tokens
- This matters for: (a) eval Q&A generation (we feed a 100K-token
  filing and ask the model to write 5 questions), (b) CRAG web
  fallback where we may need to summarize large retrieved context

### 3. Native hybrid search via Vertex AI Vector Search
- Vertex AI Vector Search supports both dense and sparse indexes
- Built-in metadata filtering
- Tree-AH and exact matching algorithms
- For the Phase 3 vector DB benchmark, this is a real "managed cloud"
  data point alongside the self-hosted Qdrant/Weaviate

### 4. Quality on long, structured documents
- Gemini 2.5 Pro scored well on long-context benchmarks
- 10-Ks are exactly the kind of long, structured document Gemini is
  designed for
- 1M-token context means we can prototype "stuff the whole 10-K into
  the prompt" approaches without infrastructure overhead

### 5. Existing familiarity
- Project lead has used Vertex AI before
- No new account setup, no new auth flow

## Tradeoffs accepted

- **Vendor lock-in**: mitigated by the pluggable backend interface.
  Swapping to OpenAI or Anthropic is a 5-line change.
- **No multi-modal for now**: Gemini is multi-modal but we're starting
  text-only. We can add image-aware ingestion later if needed.
- **text-embedding-005 has 2K token context**: limits naive
  late-chunking-on-Gemini-embeddings. Workaround: use Jina
  `jina-embeddings-v2-base-en` (8K context) just for that experiment.

## Consequences

- We need `GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default login`
  before `EMBEDDER_BACKEND=vertex` works
- All API calls go through `record_call()` for cost tracking
- We expose `EMBEDDER_BACKEND=mock` and `GENERATOR_BACKEND=mock` so the
  smoke test runs with zero GCP dependency

## What we explicitly chose NOT to do

- **Vertex AI Agent Builder / RAG Engine**: it's a managed RAG service
  that would hide the implementation. We want the implementation
  visible so the project demonstrates the techniques.
- **Vertex AI Vector Search as the only vector DB**: we want to
  benchmark it against self-hosted Qdrant and Weaviate to make an
  informed "buy vs build" decision. See ADR-004 (coming in Week 6).

## Alternatives considered

- **OpenAI**: would have been a fine choice. Slightly higher cost,
  shorter context window on text-embedding-3-small (8K vs 2K — actually
  a plus for OpenAI). Tied on most dimensions; GCP familiarity tipped
  the scale.
- **Anthropic**: best-in-class for long-context reasoning, but no
  embeddings service (we'd have to use Voyage or OpenAI for embeddings,
  introducing a second vendor). Skipped.
- **Local (Ollama)**: zero cost but 5–10x slower iteration. For a
  3-month project where we'll run thousands of experiments, this is a
  deal-breaker. We use local only for development sanity checks.

## References

- [Vertex AI text-embeddings](https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings)
- [Vertex AI Vector Search](https://cloud.google.com/vertex-ai/docs/vector-search/overview)
- [Gemini pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
