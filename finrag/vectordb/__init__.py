"""Vector-DB backends (Phase 4, ADR-005).

The interface every benchmarked store implements. Backends:
- `QdrantBackend` (`finrag/vectordb/qdrant_backend.py`) — `:memory:` offline
  or a live Qdrant URL (docker-compose `localhost:6333`).
- Weaviate / Vertex Search implementations land in later steps (they need
  live infra: Docker daemon / GCP endpoint).

Contract: backends store caller-supplied vectors (they never embed) and
return caller-owned chunk_ids ranked by similarity. Same vectors in →
same ranking out (parity with `InMemoryIndex`, verified by tests).
"""

from __future__ import annotations

from finrag.vectordb.base import VectorDBBackend
from finrag.vectordb.qdrant_backend import QdrantBackend

__all__ = ["QdrantBackend", "VectorDBBackend"]
