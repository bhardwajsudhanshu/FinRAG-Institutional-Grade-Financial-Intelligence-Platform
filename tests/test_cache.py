"""Tests for finrag/cache.py + the /ask cache wiring (STEP_045). Fully offline."""

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
from finrag.cache import AnswerCache
from finrag.chunking import Chunk
from finrag.embeddings import MockEmbedder
from finrag.generation import MockGenerator
from finrag.retrieval import InMemoryIndex


class TestAnswerCache:
    def test_miss_then_hit(self) -> None:
        c = AnswerCache()
        assert c.get("dense", 5, False, "Revenue?") is None
        c.put("dense", 5, False, "Revenue?", {"answer": "x"})
        assert c.get("dense", 5, False, "Revenue?") == {"answer": "x"}
        assert (c.hits, c.misses) == (1, 1)

    def test_normalization_folds_case_and_whitespace(self) -> None:
        c = AnswerCache()
        c.put("dense", 5, False, "  Apple   REVENUE? ", "v")
        assert c.get("dense", 5, False, "apple revenue?") == "v"

    def test_key_includes_strategy_top_k_rerank(self) -> None:
        c = AnswerCache()
        c.put("dense", 5, False, "Revenue?", "v")
        assert c.get("hybrid", 5, False, "Revenue?") is None
        assert c.get("dense", 3, False, "Revenue?") is None
        assert c.get("dense", 5, True, "Revenue?") is None

    def test_fifo_eviction_bounds_memory(self) -> None:
        c = AnswerCache(maxsize=2)
        c.put("dense", 5, False, "q1", "v1")
        c.put("dense", 5, False, "q2", "v2")
        c.put("dense", 5, False, "q3", "v3")
        assert len(c) == 2
        assert c.get("dense", 5, False, "q1") is None  # oldest evicted
        assert c.get("dense", 5, False, "q3") == "v3"

    def test_reput_overwrites_without_growth(self) -> None:
        c = AnswerCache(maxsize=2)
        c.put("dense", 5, False, "q1", "v1")
        c.put("dense", 5, False, "q1", "v2")
        assert len(c) == 1
        assert c.get("dense", 5, False, "q1") == "v2"

    def test_bad_maxsize_raises(self) -> None:
        with pytest.raises(ValueError):
            AnswerCache(maxsize=0)

    def test_stats(self) -> None:
        c = AnswerCache()
        assert c.stats()["hit_rate"] == 0.0  # no division by zero
        c.put("dense", 5, False, "q", "v")
        c.get("dense", 5, False, "q")
        c.get("dense", 5, False, "other")
        s = c.stats()
        assert (s["hits"], s["misses"], s["size"]) == (1, 1, 1)
        assert s["hit_rate"] == 0.5


def _bundle() -> tuple[dict, MockGenerator]:
    chunks = [
        Chunk(chunk_id="AAPL_x_item_7::0000",
              text="Apple net sales were $383.3 billion in fiscal 2023.",
              metadata={"ticker": "AAPL", "section_id": "item_7"}),
        Chunk(chunk_id="AAPL_x_item_7::0001",
              text="Gross margin was 37.6 percent driven by Services mix.",
              metadata={"ticker": "AAPL", "section_id": "item_7"}),
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


class CountingGenerator(MockGenerator):
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, question, contexts):
        self.calls += 1
        return super().generate(question, contexts)


class TestAskCacheWiring:
    def _client(self) -> tuple[TestClient, CountingGenerator]:
        bundle, _ = _bundle()
        gen = CountingGenerator()
        app = create_app(bundle=bundle, generator=gen)
        return TestClient(app), gen

    def test_second_identical_ask_hits_cache(self) -> None:
        client, gen = self._client()
        q = {"question": "Apple net sales were $383.3 billion in fiscal 2023.",
             "top_k": 2}
        with client:
            r1 = client.post("/ask", json=q)
            r2 = client.post("/ask", json=q)
        assert r1.headers["X-Cache"] == "MISS"
        assert r2.headers["X-Cache"] == "HIT"
        assert gen.calls == 1  # no retrieval/generation on hit
        b1, b2 = r1.json(), r2.json()
        assert b2["latency_ms"] == 0
        assert b2["answer"] == b1["answer"]
        assert b2["citations"] == b1["citations"]

    def test_case_whitespace_variant_hits(self) -> None:
        client, gen = self._client()
        with client:
            client.post("/ask", json={
                "question": "Apple net sales were $383.3 billion in fiscal 2023."})
            r = client.post("/ask", json={
                "question": "  apple NET sales were $383.3 BILLION in fiscal 2023.  "})
        assert r.headers["X-Cache"] == "HIT"
        assert gen.calls == 1

    def test_different_top_k_misses(self) -> None:
        client, gen = self._client()
        with client:
            client.post("/ask", json={
                "question": "Apple net sales were $383.3 billion in fiscal 2023.",
                "top_k": 2})
            r = client.post("/ask", json={
                "question": "Apple net sales were $383.3 billion in fiscal 2023.",
                "top_k": 1})
        assert r.headers["X-Cache"] == "MISS"
        assert gen.calls == 2
