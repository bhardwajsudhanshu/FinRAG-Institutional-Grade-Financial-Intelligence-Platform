"""FinRAG HTTP API (STEP_020 product surface).

Serves the frozen production configuration — naive chunks + hybrid RRF
retrieval (+ live Qdrant when `VECTORDB_BACKEND=qdrant`) + Vertex Flash
generation — over HTTP. See `api/main.py`.
"""

from api.main import app, create_app

__all__ = ["app", "create_app"]
