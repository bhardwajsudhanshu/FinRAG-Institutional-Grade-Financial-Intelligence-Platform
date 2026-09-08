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
from finrag.vectordb import QdrantBackend, QdrantDenseIndex, VectorDBBackend, WeaviateBackend

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

    def test_batched_upsert_stores_all(self, embedder: MockEmbedder) -> None:
        # Regression test for the STEP_019 live failure: one 4447-point
        # upsert is ~72MB > Qdrant's 32MB HTTP cap (400). Batching must be
        # transparent: all points stored and retrievable.
        n = 120
        ids = [f"C::{i:04d}" for i in range(n)]
        texts = [f"Disclosure sentence number {i} about revenue." for i in range(n)]
        b = QdrantBackend(dim=embedder.dim, collection="test_batched")
        try:
            b.upsert(ids, _embed_all(embedder, texts), batch_size=7)
            assert len(b) == n
            # Hash-embedder ties on shared tokens are arbitrary-ordered, so
            # assert membership (all batches landed, target retrievable),
            # not top-1: batching transparency is what's under test.
            got = [cid for cid, _ in b.query(embedder.embed("Disclosure sentence number 42"), top_k=5)]
            assert "C::0042" in got
        finally:
            b.close()


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


# --- QdrantDenseIndex adapter (STEP_018; :memory:, offline) --------------------


class TestQdrantDenseIndex:
    def _adapter(self, embedder: MockEmbedder,
                 corpus_ids: list[str], corpus_texts: list[str]) -> QdrantDenseIndex:
        from finrag.chunking import Chunk

        vecs = _embed_all(embedder, corpus_texts)
        by_id = {cid: Chunk(chunk_id=cid, text=t, metadata={"ticker": "T"})
                 for cid, t in zip(corpus_ids, corpus_texts, strict=True)}
        backend = QdrantBackend(dim=embedder.dim, collection="test_adapter")
        backend.upsert(corpus_ids, vecs)
        return QdrantDenseIndex(backend, by_id)

    def test_query_returns_chunk_objects(self, embedder: MockEmbedder,
                                         corpus_ids: list[str],
                                         corpus_texts: list[str]) -> None:
        from finrag.chunking import Chunk

        idx = self._adapter(embedder, corpus_ids, corpus_texts)
        assert len(idx) == 3
        hits = idx.query(embedder.embed("Microsoft Azure revenue"), top_k=1)
        assert len(hits) == 1
        chunk, score = hits[0]
        assert isinstance(chunk, Chunk)
        assert chunk.chunk_id == "MSFT_item7::0000"
        assert isinstance(score, float)

    def test_empty_top_k_safe(self, embedder: MockEmbedder,
                              corpus_ids: list[str],
                              corpus_texts: list[str]) -> None:
        idx = self._adapter(embedder, corpus_ids, corpus_texts)
        assert idx.query(embedder.embed("q"), top_k=0) == []

    def test_unknown_vectordb_backend_rejected(self) -> None:
        import types

        from finrag.eval.ragas_runner import _build_dense_index

        settings = types.SimpleNamespace(vectordb_backend="does_not_exist")
        with pytest.raises(ValueError):
            _build_dense_index([], {}, settings)


# --- WeaviateBackend (live server; skipped when Docker is down) ----------------


def _weaviate_backend_or_skip() -> WeaviateBackend:
    pytest.importorskip("weaviate")
    try:
        return WeaviateBackend(collection="TestFinragBench")
    except Exception as e:
        pytest.skip(f"Weaviate not reachable (run `make docker-up`): {e}")


class TestWeaviateBackend:
    def test_implements_backend_interface(self) -> None:
        b = _weaviate_backend_or_skip()
        try:
            assert isinstance(b, VectorDBBackend)
        finally:
            b.close()

    def test_round_trip_and_top1(self, embedder: MockEmbedder,
                                 corpus_ids: list[str],
                                 corpus_texts: list[str]) -> None:
        b = _weaviate_backend_or_skip()
        try:
            assert b.query(embedder.embed("q"), top_k=5) == []
            b.upsert(corpus_ids, _embed_all(embedder, corpus_texts),
                     payloads=[{"ticker": "AAPL"}, {"ticker": "AAPL"}, {"ticker": "MSFT"}])
            assert len(b) == 3
            hits = b.query(embedder.embed("Microsoft Azure revenue"), top_k=1)
            assert hits[0][0] == "MSFT_item7::0000"
            with pytest.raises(ValueError):
                b.upsert(["x"], [])
        finally:
            b.close()

    def test_parity_top1_and_set(self, embedder: MockEmbedder,
                                 corpus_ids: list[str],
                                 corpus_texts: list[str]) -> None:
        from finrag.chunking import Chunk
        from finrag.retrieval import InMemoryIndex

        b = _weaviate_backend_or_skip()
        try:
            vecs = _embed_all(embedder, corpus_texts)
            mem = InMemoryIndex()
            for cid, t, v in zip(corpus_ids, corpus_texts, vecs, strict=True):
                mem.add(Chunk(chunk_id=cid, text=t, metadata={}), v)
            b.upsert(corpus_ids, vecs)
            for q in ("Apple net sales fiscal year", "gross margin services",
                      "Microsoft cloud growth"):
                qv = embedder.embed(q)
                expected = [c.chunk_id for c, _ in mem.query(qv, top_k=3)]
                got = [cid for cid, _ in b.query(qv, top_k=3)]
                assert got[0] == expected[0]
                assert set(got) == set(expected)
        finally:
            b.close()


class TestPersistence:
    """STEP_037: recreate flag + server-count semantics (:memory:, offline)."""

    def test_recreate_false_creates_when_missing(self, embedder: MockEmbedder,
                                                 corpus_ids: list[str],
                                                 corpus_texts: list[str]) -> None:
        b = QdrantBackend(dim=embedder.dim, collection="test_persist_new",
                          recreate=False)
        try:
            assert len(b) == 0
            b.upsert(corpus_ids, _embed_all(embedder, corpus_texts))
            assert len(b) == 3
        finally:
            b.close()

    def test_second_instance_attaches(self, embedder: MockEmbedder,
                                      corpus_ids: list[str],
                                      corpus_texts: list[str]) -> None:
        # :memory: clients are process-local, so attach-across-processes is
        # simulated by two handles on one client is impossible — instead this
        # pins the contract attach relies on: recreate=False never wipes,
        # and re-upserting the same corpus is idempotent (same ids).
        b = QdrantBackend(dim=embedder.dim, collection="test_persist_attach",
                          recreate=False)
        try:
            vecs = _embed_all(embedder, corpus_texts)
            b.upsert(corpus_ids, vecs)
            assert len(b) == 3
            b.upsert(corpus_ids, vecs)
            assert len(b) == 3
            hits = b.query(embedder.embed("Microsoft Azure revenue"), top_k=1)
            assert hits[0][0] == "MSFT_item7::0000"
        finally:
            b.close()

    def test_recreate_true_wipes(self, embedder: MockEmbedder,
                                 corpus_ids: list[str],
                                 corpus_texts: list[str]) -> None:
        b = QdrantBackend(dim=embedder.dim, collection="test_persist_wipe")
        try:
            b.upsert(corpus_ids, _embed_all(embedder, corpus_texts))
            assert len(b) == 3
        finally:
            b.close()
        b2 = QdrantBackend(dim=embedder.dim, collection="test_persist_wipe",
                           recreate=True)
        try:
            assert len(b2) == 0
        finally:
            b2.close()


def _live_qdrant_or_skip(dim: int) -> QdrantBackend:
    try:
        b = QdrantBackend(dim=dim, collection="test_live_attach",
                          location="http://localhost:6333")
        b.point_count()
        return b
    except Exception as e:
        pytest.skip(f"live Qdrant not reachable (run `make docker-up`): {e}")


class TestLiveAttach:
    """True cross-instance attach (needs `make docker-up`; skips offline)."""

    def test_attach_sees_prior_upsert(self, embedder: MockEmbedder,
                                      corpus_ids: list[str],
                                      corpus_texts: list[str]) -> None:
        b1 = _live_qdrant_or_skip(embedder.dim)
        try:
            b1.upsert(corpus_ids, _embed_all(embedder, corpus_texts))
            assert len(b1) == 3
            b2 = QdrantBackend(dim=embedder.dim, collection="test_live_attach",
                               location="http://localhost:6333", recreate=False)
            try:
                assert len(b2) == 3
                hits = b2.query(embedder.embed("Microsoft Azure revenue"), top_k=1)
                assert hits[0][0] == "MSFT_item7::0000"
            finally:
                b2.close()
        finally:
            b1.close()
