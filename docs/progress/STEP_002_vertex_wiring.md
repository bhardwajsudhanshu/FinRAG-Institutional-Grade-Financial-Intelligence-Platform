# STEP_002 — Vertex AI wiring

- **Date:** 2026-09-05
- **Git commit:** `a4a94a2` checked with vertex ai
- **Goal:** Real Gemini + embedding calls with correct auth and cost logging.
- **Roadmap phase:** Week 1-2 Foundation (unblock real runs)

### 1. Why
Mocks prove plumbing but not quality. Need `EMBEDDER_BACKEND=vertex` / `GENERATOR_BACKEND=vertex` to run the real baseline.

### 2. What changed
- `finrag/embeddings.py` — `VertexEmbedder.embed_batch` (20/batch cap) + `GOOGLE_CLOUD_QUOTA_PROJECT` fix + `vertexai.init(project, location)`.
- `finrag/generation.py` — `VertexGenerator.generate` reads `usage_metadata` → in/out tokens → cost.
- `finrag/cost.py` — pricing: embed $0.025/M, flash in $0.075/out $0.30, pro in $1.25/out $5.00.
- `finrag/data/parse_sections.py` — parser robustness tweaks.
- `scripts/test_vertex_auth.py` — NEW: `make vertex-check` proves auth before burning money.

### 3. How it works
- Critical fix: `vertexai.init(project=...)` must run before any model call, else SDK falls back to ADC gcloud creds → 403 SERVICE_DISABLED. Same pattern in all three Vertex clients.
- `record_call` context manager: body may mutate `rec["input_tokens"]` in-place; cost recomputed on exit (`finrag/cost.py:58-101`).

### 4. How to verify
```bash
# .env: GCP_PROJECT_ID=<id>, EMBEDDER_BACKEND=vertex, GENERATOR_BACKEND=vertex
make vertex-check
make query Q="What was Apple's revenue in FY2023?"
# expect model=gemini-2.5-flash and non-zero cost
```

### 5. Result
Real Vertex path works. Unblocked STEP_003 full eval (which burned ~$0.03-0.04 per 139-Q run).

### 6. How to recall
- Commit: `git show a4a94a2 --stat`
- Auth script: `scripts/test_vertex_auth.py`
- Pricing: `finrag/cost.py:28-40`

### 7. Next step
STEP_003 ingests all 20 tickers and builds the frozen 139-Q eval set.
