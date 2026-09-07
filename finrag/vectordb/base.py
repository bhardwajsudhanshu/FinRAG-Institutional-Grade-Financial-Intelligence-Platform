"""Backend contract for the vector-DB benchmark (ADR-005).

Vectors are L2-normalized embeddings supplied by the caller (mock or
Vertex — backends never embed). Scores are cosine similarities (higher
is better), matching `InMemoryIndex` so parity is checkable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class VectorDBBackend(ABC):
    """Minimal store contract every benchmarked DB implements."""

    @abstractmethod
    def upsert(self, chunk_ids: list[str], vectors: list[list[float]],
               payloads: list[dict] | None = None) -> None:
        """Store vectors under chunk_ids (parallel lists). Idempotent."""

    @abstractmethod
    def query(self, query_vector: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        """Return [(chunk_id, cosine_score)] top-k, best first."""

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def close(self) -> None:
        """Release resources (connections, temp collections)."""
