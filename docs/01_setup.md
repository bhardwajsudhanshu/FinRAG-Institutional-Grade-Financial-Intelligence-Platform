# Setup Guide

This guide gets FinRAG running on a Windows machine. Total time: ~10 minutes.

## Prerequisites

- **Python 3.11+** on PATH (this project uses 3.14)
- **`uv`** installed (`pip install uv` if you don't have it)
- **Docker Desktop** (only needed when running Qdrant/Weaviate/Redis locally — not required for the Week 1 smoke test)
- **GCP project with Vertex AI enabled** (only needed when you wire real Gemini; the smoke test uses mock backends)

## 1. Clone & install

```bash
# From the project root
cd "F:/projects/FinRAG - Institutional-Grade Financial Intelligence Platform"
make env
```

`make env` does three things:
1. Creates a project-local venv at `.venv/` (on **F: drive**)
2. Installs all dependencies declared in `pyproject.toml` into it
3. uv's cache is redirected to `F:/.uv-cache` (see `pyproject.toml` `[tool.uv]` block)

The C: drive is **not** touched by this project's operations.

## 2. Environment variables

```bash
cp .env.example .env
```

Open `.env` and set the values you need. For the Week 1 smoke test, **the defaults work** — `EMBEDDER_BACKEND=mock` and `GENERATOR_BACKEND=mock` give you a fully working pipeline with no network calls.

## 3. Smoke test (no GCP required)

```bash
# Ingest the synthetic AAPL 10-K (offline-safe)
make ingest-sample

# Ask a question
make query Q="What are Apple's main risk factors?"
```

Expected output: an answer with `[AAPL_2023-11-03_item_1a::0001]` style citations, plus a token/cost log line.

## 4. Wiring real Vertex AI (when ready)

### 4a. Set up GCP

1. Create a GCP project (or use an existing one)
2. Enable the **Vertex AI API** (`https://console.cloud.google.com/apis/library/aiplatform.googleapis.com`)
3. Either:
   - **(Recommended)** Run `gcloud auth application-default login` once on this machine. This writes a credentials file to `%APPDATA%\gcloud\` (C: drive, but it's tiny — single file, a few KB).
   - **(Alternative)** Create a service account, download the JSON key, and set `GOOGLE_APPLICATION_CREDENTIALS` in `.env` to its path.

### 4b. Update .env

```env
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
EMBEDDER_BACKEND=vertex
GENERATOR_BACKEND=vertex
```

### 4c. Verify

```bash
make query Q="What was Apple's revenue in FY2023?"
```

You should see the model ID change from `mock-generator` to `gemini-2.5-flash` and a non-zero cost in the output.

### 4d. Vertex AI Vector Search (Phase 3)

When we reach Phase 3 we'll add a `scripts/deploy_vertex_index.py` and a corresponding `scripts/teardown_vertex.py`. **Don't leave the index running between sessions** — Vertex AI charges ~$0.10/hr while an index endpoint is deployed.

## 5. Docker services (Qdrant, Weaviate, Redis, Postgres)

```bash
make docker-up
```

This starts 4 containers on default ports:
- Qdrant: `localhost:6333` (REST), `localhost:6334` (gRPC)
- Weaviate: `localhost:8080`
- Redis: `localhost:6379`
- Postgres: `localhost:5432` (user/pass/db = `finrag`/`finrag`/`finrag`)

**Note on C: drive usage:** Docker Desktop stores its image and volume data on C: by default (around `C:\ProgramData\Docker`). This is **not** specific to FinRAG — it's a Docker Desktop setting. If you want to move it to F: drive:
1. Docker Desktop → Settings → Resources → Advanced
2. Click the disk icon next to "Disk image location"
3. Move to e.g. `F:\.docker-data`
4. Docker will restart and re-pull images (~3-5 GB). Do this once.

We don't touch that system setting from this project.

## 6. Verifying the install

```bash
make test         # runs pytest (no tests yet, will pass)
make lint         # ruff check
make query Q="What was Apple's revenue in FY2023?"
```

If the `make query` output looks right, you're set.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uv: command not found` | `pip install uv` (one-time) |
| `EMBEDDER_BACKEND=vertex` but no auth | Run `gcloud auth application-default login` |
| `No sections parsed` on a real 10-K | The section regex doesn't match this filing's format. File an issue with the filing and we'll iterate the parser. |
| Port 6333 already in use | Some other service is using it. Change the port mapping in `docker-compose.yml`. |
| Cost log file growing huge | Truncate `data/runtime_costs.jsonl` weekly; it has lines per API call. |

## What NOT to commit

The `.gitignore` covers all of this, but for the record:
- `.env` (your secrets)
- `.venv/` (the local venv)
- `data/raw/` (downloaded filings — can be hundreds of MB)
- `data/runtime_costs.jsonl` (sensitive cost data, may include billing info)
- `secrets/` (any service account keys)
