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
import re
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


# --- exp_020/021: BM25 + hybrid RRF (Phase 3, ADR-004) ------------------------
#
# BM25 is the lexical complement to dense cosine: exact numbers, tickers,
# and section names ("Item 1A", "$383.3") score highly even when the
# embedding buries them in narrative. rank-bm25 needs no model, no
# downloads, no network — indexing is pure CPU. Hybrid fuses both sides
# with Reciprocal Rank Fusion (ranks, not raw scores, so the incomparable
# cosine-vs-BM25 scales never meet).

_BM25_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize_for_bm25(text: str) -> list[str]:
    """Lowercase alphanumeric tokens. Regex-only (no NLTK data needed)."""
    return _BM25_TOKEN_RE.findall(text.lower())


class BM25Index:
    """Lexical index over a fixed chunk list. No embeddings anywhere."""

    def __init__(self, chunks: list[Chunk]):
        self._chunks = list(chunks)
        self._bm25 = None
        if chunks:
            from rank_bm25 import BM25Okapi  # lazy: only needed for bm25/hybrid runs

            self._bm25 = BM25Okapi([tokenize_for_bm25(c.text) for c in chunks])

    def __len__(self) -> int:
        return len(self._chunks)

    def query(self, question: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Return (chunk, raw BM25 score) for the top-k lexical matches."""
        if self._bm25 is None or top_k <= 0:
            return []
        scores = self._bm25.get_scores(tokenize_for_bm25(question))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [(self._chunks[i], float(scores[i])) for i in ranked]


def build_bm25_index(chunks: list[Chunk]) -> BM25Index:
    """Build a lexical index. CPU-only: embeds nothing, costs nothing."""
    return BM25Index(chunks)


def reciprocal_rank_fusion(
    ranked_id_lists: list[list[str]],
    rrf_k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse ranked chunk-id lists into [(chunk_id, fused_score)].

    score(d) = sum over lists of 1 / (rrf_k + rank + 1). Higher is better.
    k=60 is the literature standard (Cormack et al. 2009); ranks are
    0-based here, hence the +1.
    """
    fused: dict[str, float] = {}
    for ids in ranked_id_lists:
        for rank, cid in enumerate(ids):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
    return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)


def retrieve_with_strategy(
    bundle: dict,
    question: str,
    top_k: int = 5,
    rrf_k: int = 60,
    per_side_k: int = 20,
) -> list[tuple[Chunk, float]]:
    """Strategy dispatcher. `bundle` comes from `build_index_for_qa_pairs`.

    - dense: embed question, cosine over dense index (exp_001-004 path, unchanged).
    - bm25: lexical query only (no embedding calls at all).
    - hybrid: top-`per_side_k` from each side, RRF-fused to top_k.
    Raises ValueError on unknown strategy so misconfiguration is loud.
    """
    strategy = bundle.get("strategy", "dense")
    if strategy == "dense":
        return retrieve(bundle["dense"], question, top_k=top_k)
    if strategy == "bm25":
        return bundle["bm25"].query(question, top_k=top_k)
    if strategy == "hybrid":
        dense_hits = retrieve(bundle["dense"], question, top_k=per_side_k)
        bm25_hits = bundle["bm25"].query(question, top_k=per_side_k)
        fused = reciprocal_rank_fusion(
            [[c.chunk_id for c, _ in dense_hits], [c.chunk_id for c, _ in bm25_hits]],
            rrf_k=rrf_k,
        )
        by_id = bundle["chunks_by_id"]
        return [(by_id[cid], score) for cid, score in fused[:top_k] if cid in by_id]
    raise ValueError(
        f"Unknown retrieval strategy {strategy!r}. Valid options: ['dense', 'bm25', 'hybrid']"
    )
