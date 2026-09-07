"""Qdrant backend (exp_050). `:memory:` for offline benchmarks, URL for live.

Usage:
    backend = QdrantBackend(dim=768)                      # offline, :memory:
    backend = QdrantBackend(dim=768, location="http://localhost:6333")  # docker
    backend.upsert(chunk_ids, vectors, payloads)
    backend.query(qvec, top_k=5)  # -> [(chunk_id, cosine_score)]

`qdrant-client` is an optional (`vectordbs`) dependency: imported lazily
so `finrag.vectordb` imports cleanly without it (calls then raise with a
clear message instead of ImportError at import time).
"""

from __future__ import annotations

from typing import Any

from finrag.vectordb.base import VectorDBBackend


class QdrantBackend(VectorDBBackend):
    """Qdrant-backed vector store over caller-supplied normalized vectors."""

    def __init__(self, dim: int, collection: str = "finrag",
                 location: str = ":memory:") -> None:
        try:
            from qdrant_client import QdrantClient  # type: ignore
            from qdrant_client.http import models  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "QdrantBackend needs the 'vectordbs' extra: "
                "uv sync --extra vectordbs"
            ) from e
        self._models = models
        self._collection = collection
        self._dim = dim
        self._client = QdrantClient(location=location)
        if self._client.collection_exists(collection):
            self._client.delete_collection(collection)
        self._client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        self._count = 0

    def __len__(self) -> int:
        return self._count

    def upsert(self, chunk_ids: list[str], vectors: list[list[float]],
               payloads: list[dict] | None = None, batch_size: int = 500) -> None:
        """Batch-upsert (Qdrant HTTP caps a request at 32MB — one 4447-point
        upsert is ~72MB and 400s. 500-point batches are ~8MB each)."""
        if len(chunk_ids) != len(vectors):
            raise ValueError("chunk_ids and vectors must be parallel lists")
        models = self._models
        points = [
            models.PointStruct(
                id=i + self._count,
                vector=list(vec),
                payload={"chunk_id": cid, **(payloads[i] if payloads else {})},
            )
            for i, (cid, vec) in enumerate(zip(chunk_ids, vectors, strict=True))
        ]
        for start in range(0, len(points), batch_size):
            self._client.upsert(collection_name=self._collection,
                                points=points[start:start + batch_size])
        self._count += len(points)

    def query(self, query_vector: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        if self._count == 0 or top_k <= 0:
            return []
        res = self._client.query_points(
            collection_name=self._collection,
            query=list(query_vector),
            limit=top_k,
        )
        return [
            (str(p.payload.get("chunk_id", p.id)), float(p.score))
            for p in res.points
        ]

    def close(self) -> None:
        self._client.close()

    # For tests that need raw access without leaking the client type.
    @property
    def _debug_client(self) -> Any:
        return self._client


class QdrantDenseIndex:
    """Drop-in for `InMemoryIndex` backed by a live Qdrant collection.

    The eval runner's dense path calls `index.query(qvec, top_k)` and
    expects `[(Chunk, score)]`; Qdrant returns ids, so this adapter maps
    them back through `chunks_by_id`. Scores are Qdrant cosine (parity
    1.0 with brute force, STEP_017).
    """

    def __init__(self, backend: QdrantBackend, chunks_by_id: dict) -> None:
        self._backend = backend
        self._chunks_by_id = chunks_by_id

    def __len__(self) -> int:
        return len(self._backend)

    def query(self, query_embedding: list[float], top_k: int = 5) -> list[tuple]:
        out = []
        for cid, score in self._backend.query(query_embedding, top_k=top_k):
            chunk = self._chunks_by_id.get(cid)
            if chunk is not None:
                out.append((chunk, score))
        return out
