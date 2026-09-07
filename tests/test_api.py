"""API tests (STEP_020). Fully offline: injected bundle + MockGenerator.

Covers: health before/after build, ask happy path + citations shape,
blank-question 422, leaderboard passthrough, and the production lifespan
path (real filings, mock backends — no Vertex, no Docker).
"""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import create_app
from finrag.chunking import Chunk
from finrag.embeddings import MockEmbedder
from finrag.generation import MockGenerator
from finrag.retrieval import InMemoryIndex


def _bundle() -> tuple[dict, MockGenerator]:
    chunks = [
        Chunk(chunk_id="AAPL_x_item_7::0000",
              text="Apple net sales were $383.3 billion in fiscal 2023.",
              metadata={"ticker": "AAPL", "section_id": "item_7"}),
        Chunk(chunk_id="AAPL_x_item_7::0001",
              text="Gross margin was 37.6 percent driven by Services mix.",
              metadata={"ticker": "AAPL", "section_id": "item_7"}),
        Chunk(chunk_id="MSFT_x_item_7::0000",
              text="Microsoft Azure revenue grew 30 percent year over year.",
              metadata={"ticker": "MSFT", "section_id": "item_7"}),
    ]
    emb = MockEmbedder(dim=64)
    mem = InMemoryIndex()
    for c in chunks:
        mem.add(c, emb.embed(c.text))
    bundle = {"strategy": "dense", "dense": mem, "bm25": None,
              "chunks_by_id": {c.chunk_id: c for c in chunks},
              "n_chunks": len(chunks), "vectordb_backend": "in-memory",
              "embedder": emb}
    return bundle, MockGenerator()


def _client(reranker=None) -> TestClient:
    bundle, gen = _bundle()
    app = create_app(bundle=bundle, generator=gen,
                     chunk_id_to_text={c.chunk_id: c.text for c in
                                       bundle["chunks_by_id"].values()},
                     reranker=reranker)
    return TestClient(app)


class TestHealth:
    def test_health_ok_with_bundle(self) -> None:
        with _client() as client:
            r = client.get("/health")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "ok"
            assert body["n_chunks"] == 3
            assert body["retrieval_strategy"] == "dense"

    def test_health_503_before_build(self) -> None:
        # No lifespan run (no `with` block) -> index never builds -> 503.
        client = TestClient(create_app())
        r = client.get("/health")
        assert r.status_code == 503


class TestAsk:
    def test_ask_returns_cited_answer(self) -> None:
        # Query is verbatim chunk text: identical hash vector -> cosine 1.0,
        # so top-1 is deterministic regardless of hash collisions elsewhere.
        with _client() as client:
            r = client.post("/ask", json={
                "question": "Apple net sales were $383.3 billion in fiscal 2023.",
                "top_k": 2,
            })
            assert r.status_code == 200
            body = r.json()
            assert body["answer"]
            assert len(body["citations"]) == 2
            assert body["citations"][0]["ticker"] == "AAPL"
            assert body["model"] == "mock-generator"
            assert body["latency_ms"] >= 0

    def test_ask_rejects_blank_question(self) -> None:
        with _client() as client:
            r = client.post("/ask", json={"question": "   "})
            assert r.status_code in (422, 500)

    def test_ask_rejects_empty_question_schema(self) -> None:
        with _client() as client:
            r = client.post("/ask", json={"question": ""})
            assert r.status_code == 422

    def test_ask_rejects_bad_top_k(self) -> None:
        with _client() as client:
            r = client.post("/ask", json={"question": "Revenue?", "top_k": 99})
            assert r.status_code == 422


class TestBestAnswerMode:
    def test_default_is_not_reranked(self) -> None:
        with _client() as client:
            r = client.post("/ask", json={
                "question": "Apple net sales were $383.3 billion in fiscal 2023."})
            assert r.status_code == 200
            assert r.json()["reranked"] is False

    def test_rerank_flag_reorders_via_injected_reranker(self) -> None:
        from finrag.rerank import NoopReranker

        class ReverseReranker(NoopReranker):
            def rerank(self, question, items, top_k=5):
                return list(reversed(items[:top_k]))

        with _client(reranker=ReverseReranker()) as client:
            plain = client.post("/ask", json={
                "question": "Apple net sales were $383.3 billion in fiscal 2023."}).json()
            best = client.post("/ask", json={
                "question": "Apple net sales were $383.3 billion in fiscal 2023.",
                "rerank": True}).json()
            assert best["reranked"] is True
            plain_ids = [c["chunk_id"] for c in plain["citations"]]
            best_ids = [c["chunk_id"] for c in best["citations"]]
            assert best_ids == list(reversed(plain_ids))


class TestLeaderboard:
    def test_leaderboard_passthrough(self) -> None:
        with _client() as client:
            r = client.get("/leaderboard")
            assert r.status_code == 200
            body = r.json()
            assert "categories" in body and "experiments" in body


class TestLifespanBuild:
    def test_lifespan_builds_from_filings_with_mocks(self, monkeypatch) -> None:
        """Production path with mock backends: parses real filings, $0."""
        from finrag.config import get_settings

        monkeypatch.setenv("EMBEDDER_BACKEND", "mock")
        monkeypatch.setenv("GENERATOR_BACKEND", "mock")
        # The machine may export its own VECTORDB_BACKEND (OS env beats the
        # .env file in pydantic-settings); pin it so tests never depend on
        # untracked local environment.
        monkeypatch.setenv("VECTORDB_BACKEND", "in-memory")
        get_settings.cache_clear()
        try:
            with TestClient(create_app()) as client:
                r = client.get("/health")
                assert r.status_code == 200
                assert r.json()["n_chunks"] > 100
                r = client.post("/ask", json={"question": "What was Apple's revenue in FY2023?"})
                assert r.status_code == 200
                assert r.json()["citations"]
        finally:
            get_settings.cache_clear()
