"""Weaviate backend (exp_051). Needs a live server (docker-compose `weaviate`).

Usage:
    backend = WeaviateBackend(collection="FinragBench")  # localhost:8080
    backend.upsert(chunk_ids, vectors, payloads)
    backend.query(qvec, top_k=5)  # -> [(chunk_id, cosine_similarity)]

Bring-your-own-vectors (`vectorizer_config=none`): the compose file's
text2vec-transformers module is never invoked, so no model download.
Scores are `1 - cosine_distance` (Weaviate reports distance).

`weaviate-client` is an optional (`vectordbs`) dependency: imported
lazily with a clear error, same convention as the Qdrant backend.
"""

from __future__ import annotations

from typing import Any

from finrag.vectordb.base import VectorDBBackend


class WeaviateBackend(VectorDBBackend):
    """Weaviate-backed vector store over caller-supplied normalized vectors."""

    def __init__(self, collection: str = "FinragBench",
                 host: str = "localhost", port: int = 8080) -> None:
        try:
            import weaviate  # type: ignore
            from weaviate.classes.config import (  # type: ignore
                Configure,
                DataType,
                Property,
            )
        except ImportError as e:
            raise RuntimeError(
                "WeaviateBackend needs the 'vectordbs' extra: "
                "uv sync --extra vectordbs"
            ) from e
        self._collection_name = collection
        client = weaviate.connect_to_local(host=host, port=port)
        if not client.is_ready():
            client.close()
            raise RuntimeError(f"Weaviate not ready at {host}:{port}. Run `make docker-up`.")
        self._client = client
        if client.collections.exists(collection):
            client.collections.delete(collection)
        self._collection = client.collections.create(
            name=collection,
            vector_config=Configure.Vectors.self_provided(),
            properties=[
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="ticker", data_type=DataType.TEXT),
                Property(name="section_id", data_type=DataType.TEXT),
            ],
        )
        self._count = 0

    def __len__(self) -> int:
        return self._count

    def upsert(self, chunk_ids: list[str], vectors: list[list[float]],
               payloads: list[dict] | None = None, batch_size: int = 500) -> None:
        """Batch-insert (Weaviate gRPC caps a single batch at ~10MB, so one
        `insert_many` for thousands of 768-dim vectors fails)."""
        if len(chunk_ids) != len(vectors):
            raise ValueError("chunk_ids and vectors must be parallel lists")
        from weaviate.classes.data import DataObject  # type: ignore

        objs = [
            DataObject(
                properties={
                    "chunk_id": cid,
                    "ticker": (payloads[i].get("ticker", "") if payloads else ""),
                    "section_id": (payloads[i].get("section_id", "") if payloads else ""),
                },
                vector=list(vec),
            )
            for i, (cid, vec) in enumerate(zip(chunk_ids, vectors, strict=True))
        ]
        for start in range(0, len(objs), batch_size):
            self._collection.data.insert_many(objs[start:start + batch_size])
        self._count += len(objs)

    def query(self, query_vector: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        if self._count == 0 or top_k <= 0:
            return []
        from weaviate.classes.query import MetadataQuery  # type: ignore

        res = self._collection.query.near_vector(
            near_vector=list(query_vector),
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
        )
        out = []
        for obj in res.objects:
            dist = obj.metadata.distance if obj.metadata else None
            score = 1.0 - dist if dist is not None else 0.0
            out.append((str(obj.properties.get("chunk_id", obj.uuid)), float(score)))
        return out

    def close(self) -> None:
        self._client.close()

    @property
    def _debug_collection(self) -> Any:
        return self._collection
