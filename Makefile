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
	uv run python scripts/patch_langchain_vertexai_shim.py

install: env ## Alias for `make env`

vertex-check: ## Verify Vertex AI auth is wired correctly
	uv run python scripts/test_vertex_auth.py

patch-ragas: ## Re-apply the langchain_community.chat_models.vertexai shim
	uv run python scripts/patch_langchain_vertexai_shim.py

# --- Common workflows -------------------------------------------------------
ingest: ## Ingest all 20 tickers × 3 years from SEC EDGAR
	uv run python -m finrag.cli.ingest

ingest-sample: ## Ingest 1 sample filing (Apple 10-K FY2023) for smoke test
	uv run python -m finrag.cli.ingest --sample

query: ## Ask a question (usage: make query Q="What was Apple's revenue in FY2023?")
	uv run python -m finrag.cli.ask "$(Q)"

eval: ## Run exp_001 baseline against the eval set
	uv run python -m finrag.cli.eval --exp exp_001_naive_baseline

eval-smoke: ## Run eval on the first 5 Q's (no full eval set required)
	uv run python -m finrag.cli.eval --exp exp_001_smoke --qa-path data/eval/qa_pairs_smoke.jsonl --out-csv results/smoke_experiments.csv --top-k 5

eval-nightly: ## Full eval run + leaderboard refresh (for nightly cron)
	uv run python -m finrag.cli.eval --exp exp_001_naive_baseline
	uv run python tests/eval/update_leaderboard.py

leaderboard: ## Rebuild results/leaderboard.json + write an immutable snapshot
	uv run python tests/eval/update_leaderboard.py
	@echo ""
	@echo "Immutability: rolling leaderboard.json is overwritten; an immutable"
	@echo "timestamped copy is written to results/leaderboard_snapshots/."
	@echo "Past experiment rows in results/experiments.csv are never modified."

qa-gen: ## Generate the 200-Q eval set (slow, ~80 min on Vertex)
	uv run python tests/eval/generate_qa_pairs.py

qa-gen-smoke: ## Generate a 2-Q smoke eval set
	uv run python tests/eval/generate_qa_pairs.py --limit 1 --per-filing 5 --out data/eval/qa_pairs_smoke.jsonl

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

test-eval: ## Run eval unit tests (fast, no Vertex calls)
	uv run pytest tests/eval/test_ragas_runner.py -v

lint: ## Lint with ruff
	uv run ruff check finrag/ tests/

format: ## Auto-format with ruff
	uv run ruff format finrag/ tests/
	uv run ruff check --fix finrag/ tests/

clean: ## Remove caches (NEVER touches the venv on F: or the .env)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf data/chroma data/embeddings_cache
