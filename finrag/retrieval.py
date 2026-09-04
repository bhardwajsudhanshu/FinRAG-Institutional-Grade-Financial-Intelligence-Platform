"""In-memory retrieval over an in-memory index.

This is intentionally minimal: a brute-force cosine-similarity search over
all stored chunks. It will be replaced by real vector DB backends in Phase 3
(Qdrant, Weaviate, Vertex AI Vector Search). The interface is stable so
the swap is one line.

Why brute force is fine for exp_001:
- Smoke test has ~30 chunks
- The baseline is "does the right chunk come up for a real question"
- Real benchmarking comes in Phase 3
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from finrag.chunking import Chunk
from finrag.embeddings import get_embedder
from finrag.generation import Citation


@dataclass
class IndexedChunk:
    """A chunk plus its pre-computed embedding (kept together for the in-memory index)."""

    chunk: Chunk
    embedding: list[float]


class InMemoryIndex:
    """Trivial in-memory vector index. Cosine similarity over L2-normalized vectors."""

    def __init__(self):
        self._items: list[IndexedChunk] = []

    def add(self, chunk: Chunk, embedding: list[float]) -> None:
        self._items.append(IndexedChunk(chunk=chunk, embedding=embedding))

    def __len__(self) -> int:
        return len(self._items)

    def query(self, query_embedding: list[float], top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Return (chunk, cosine_score) for the top-k most similar chunks."""
        if not self._items:
            return []
        qn = _normalize(query_embedding)
        scored: list[tuple[Chunk, float]] = []
        for item in self._items:
            score = _dot(qn, _normalize(item.embedding))
            scored.append((item.chunk, score))
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:top_k]


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def build_index(chunks: list[Chunk], index_path: Path | None = None) -> InMemoryIndex:
    """Embed all chunks and add to a fresh InMemoryIndex.

    If `index_path` is given, also persist chunk metadata to a parquet for
    auditability (and so we can rebuild the index from disk if needed).
    """
    embedder = get_embedder()
    idx = InMemoryIndex()
    # Batch embed for speed (mock and vertex both have batch paths)
    texts = [c.text for c in chunks]
    vectors = embedder.embed_batch(texts)
    for chunk, vec in zip(chunks, vectors):
        idx.add(chunk, vec)
    if index_path is not None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame([c.to_dict() for c in chunks])
        df.to_parquet(index_path, index=False)
    return idx


def retrieve(
    index: InMemoryIndex,
    question: str,
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    """Embed a question and return the top-k most similar chunks."""
    embedder = get_embedder()
    q_vec = embedder.embed(question)
    return index.query(q_vec, top_k=top_k)


def results_to_citations(results: list[tuple[Chunk, float]]) -> list[Citation]:
    return [
        Citation(
            chunk_id=chunk.chunk_id,
            score=score,
            metadata=chunk.metadata,
        )
        for chunk, score in results
    ]
