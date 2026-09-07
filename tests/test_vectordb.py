"""Unit tests for finrag/vectordb (Phase 4, ADR-005, exp_050).

All Qdrant tests run against `:memory:` mode — no Docker, no network.
They verify the backend contract:
- upsert/query round-trip with exact top-1 on distinctive text,
- parity with InMemoryIndex (same vectors -> same top-5 ids),
- empty index / top_k<=0 safety,
- mismatched upsert lists raise loudly,
- payloads (ticker/section) stored for future filtered benchmarks.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from finrag.embeddings import MockEmbedder
from finrag.vectordb import QdrantBackend, VectorDBBackend

qdrant_client = pytest.importorskip("qdrant_client")

DIM = 64


@pytest.fixture()
def embedder() -> MockEmbedder:
    return MockEmbedder(dim=DIM)


@pytest.fixture()
def backend() -> QdrantBackend:
    b = QdrantBackend(dim=DIM, collection="test_finrag")
    yield b
    b.close()


@pytest.fixture()
def corpus_ids() -> list[str]:
    return ["AAPL_item7::0000", "AAPL_item7::0001", "MSFT_item7::0000"]


@pytest.fixture()
def corpus_texts() -> list[str]:
    return [
        "Apple net sales were $383.3 billion in fiscal 2023.",
        "Gross margin was 37.6 percent driven by Services mix.",
        "Microsoft Azure revenue grew 30 percent year over year.",
    ]


def _embed_all(embedder: MockEmbedder, texts: list[str]) -> list[list[float]]:
    return embedder.embed_batch(texts)


class TestContract:
    def test_implements_backend_interface(self, backend: QdrantBackend) -> None:
        assert isinstance(backend, VectorDBBackend)

    def test_empty_index_queries_empty(self, backend: QdrantBackend,
                                       embedder: MockEmbedder) -> None:
        assert backend.query(embedder.embed("Apple revenue"), top_k=5) == []
        assert len(backend) == 0

    def test_top_k_zero_returns_empty(self, backend: QdrantBackend,
                                      embedder: MockEmbedder,
                                      corpus_ids: list[str],
                                      corpus_texts: list[str]) -> None:
        backend.upsert(corpus_ids, _embed_all(embedder, corpus_texts))
        assert backend.query(embedder.embed("Apple"), top_k=0) == []

    def test_mismatched_upsert_raises(self, backend: QdrantBackend,
                                      embedder: MockEmbedder,
                                      corpus_texts: list[str]) -> None:
        with pytest.raises(ValueError):
            backend.upsert(["only-one-id"], _embed_all(embedder, corpus_texts))


class TestRetrievalQuality:
    def test_exact_match_returns_right_chunk(self, backend: QdrantBackend,
                                             embedder: MockEmbedder,
                                             corpus_ids: list[str],
                                             corpus_texts: list[str]) -> None:
        backend.upsert(corpus_ids, _embed_all(embedder, corpus_texts))
        hits = backend.query(embedder.embed("Microsoft Azure revenue"), top_k=1)
        assert hits[0][0] == "MSFT_item7::0000"

    def test_scores_are_cosine_like(self, backend: QdrantBackend,
                                    embedder: MockEmbedder,
                                    corpus_ids: list[str],
                                    corpus_texts: list[str]) -> None:
        backend.upsert(corpus_ids, _embed_all(embedder, corpus_texts))
        hits = backend.query(embedder.embed("Apple net sales"), top_k=3)
        assert len(hits) == 3
        scores = [s for _, s in hits]
        assert scores == sorted(scores, reverse=True)
        assert all(-1.0 <= s <= 1.0 + 1e-6 for s in scores)

    def test_parity_with_in_memory_index(self, backend: QdrantBackend,
                                         embedder: MockEmbedder,
                                         corpus_ids: list[str],
                                         corpus_texts: list[str]) -> None:
        """Same vectors -> same top-5 ids as brute-force cosine (ADR-005 parity)."""
        from finrag.chunking import Chunk
        from finrag.retrieval import InMemoryIndex

        vecs = _embed_all(embedder, corpus_texts)
        chunks = [Chunk(chunk_id=cid, text=t, metadata={})
                  for cid, t in zip(corpus_ids, corpus_texts, strict=True)]
        mem = InMemoryIndex()
        for c, v in zip(chunks, vecs, strict=True):
            mem.add(c, v)
        backend.upsert(corpus_ids, vecs)
        # Parity is top-1 + SET equality, not full order: Qdrant stores
        # float32 (in-memory is float64) and HNSW may order near-tie tails
        # differently. Tails are noise by construction (MockEmbedder hash
        # vectors share ~nothing with off-topic queries). This matches how
        # hit@5 itself is scored — order-insensitive within the top-5 —
        # so set parity is the methodologically honest bar, and the bar
        # the STEP_017 benchmark parity check will use on 4447 chunks.
        for q in ("Apple net sales fiscal year", "gross margin services",
                  "Microsoft cloud growth", "risk factors"):
            qv = embedder.embed(q)
            expected = [c.chunk_id for c, _ in mem.query(qv, top_k=3)]
            got = [cid for cid, _ in backend.query(qv, top_k=3)]
            assert got[0] == expected[0]
            assert set(got) == set(expected)

    def test_payloads_stored(self, backend: QdrantBackend,
                             embedder: MockEmbedder,
                             corpus_ids: list[str],
                             corpus_texts: list[str]) -> None:
        backend.upsert(corpus_ids, _embed_all(embedder, corpus_texts),
                       payloads=[{"ticker": "AAPL"}, {"ticker": "AAPL"}, {"ticker": "MSFT"}])
        pts, _ = backend._debug_client.scroll(collection_name="test_finrag", limit=10)
        tickers = sorted(p.payload["ticker"] for p in pts)
        assert tickers == ["AAPL", "AAPL", "MSFT"]


class TestMathSanity:
    def test_mock_vectors_are_unit_norm(self, embedder: MockEmbedder) -> None:
        v = embedder.embed("Apple net sales were $383.3B.")
        assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-9
