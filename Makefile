# FinRAG — convenience Makefile
# Windows users: install `make` via `choco install make` or use WSL.
# All commands assume you're in the project root and have uv installed.
# The venv lives in .venv/ on F: drive; uv cache at F:/.uv-cache.

.PHONY: help install setup env dev test lint format ingest ingest-sample query eval ui docker-up docker-down docker-logs clean vertex-check

help: ## Show this help
	@uv run python -c "import re; print('\n'.join(sorted(re.findall(r'^([a-zA-Z_-]+):.*?## (.*)', open('Makefile').read(), re.MULTILINE))))"

# --- Environment ------------------------------------------------------------
env: ## Create venv on F: drive and install deps
	uv venv .venv --python 3.11
	uv sync --extra dev --extra eval --extra vectordbs

install: env ## Alias for `make env`

vertex-check: ## Verify Vertex AI auth is wired correctly
	uv run python scripts/test_vertex_auth.py

# --- Common workflows -------------------------------------------------------
ingest: ## Ingest all 20 tickers × 3 years from SEC EDGAR
	uv run python -m finrag.cli.ingest

ingest-sample: ## Ingest 1 sample filing (Apple 10-K FY2023) for smoke test
	uv run python -m finrag.cli.ingest --sample

query: ## Ask a question (usage: make query Q="What was Apple's revenue in FY2023?")
	uv run python -m finrag.cli.ask "$(Q)"

eval: ## Run exp_001 baseline against the eval set
	uv run python -m finrag.cli.eval --exp exp_001_naive_baseline

ui: ## Launch the Streamlit dashboard
	uv run streamlit run ui/streamlit_app.py

# --- Docker -----------------------------------------------------------------
docker-up: ## Start Qdrant, Weaviate, Redis, Postgres
	docker compose up -d
	@echo "Waiting for services..."
	@sleep 5
	@docker compose ps

docker-down: ## Stop all docker services
	docker compose down

docker-logs: ## Tail docker logs
	docker compose logs -f

# --- Dev hygiene ------------------------------------------------------------
test: ## Run tests
	uv run pytest -ra

lint: ## Lint with ruff
	uv run ruff check finrag/ tests/

format: ## Auto-format with ruff
	uv run ruff format finrag/ tests/
	uv run ruff check --fix finrag/ tests/

clean: ## Remove caches (NEVER touches the venv on F: or the .env)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf data/chroma data/embeddings_cache
