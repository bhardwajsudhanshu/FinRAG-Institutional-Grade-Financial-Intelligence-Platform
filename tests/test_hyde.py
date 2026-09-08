"""Unit tests for finrag/hyde.py (STEP_039, exp_044). Offline.

Flash writing is injected via `generate_fn` fakes; retrieval runs on
MockEmbedder. Covers writer hygiene, anchored fusion, empty fallback,
and determinism.
"""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from finrag.chunking import Chunk
from finrag.hyde import HyDEGenerator, get_hyde_generator, hyde_fuse, hyde_retrieve


def _mk(cid: str, text: str) -> Chunk:
    return Chunk(chunk_id=cid, text=text, metadata={})


def _bundle():
    from finrag.embeddings import MockEmbedder
    from finrag.retrieval import InMemoryIndex

    chunks = [
        _mk("c0", "Apple net sales were $383.3 billion in fiscal 2023."),
        _mk("c1", "Gross margin was 37.6 percent driven by Services mix."),
        _mk("c2", "Microsoft Azure revenue grew 30 percent year over year."),
        _mk("c3", "The board declared a quarterly dividend of twenty-four cents."),
    ]
    emb = MockEmbedder(dim=64)
    idx = InMemoryIndex()
    for c in chunks:
        idx.add(c, emb.embed(c.text))
    return {"strategy": "dense", "dense": idx, "bm25": None,
            "chunks_by_id": {c.chunk_id: c for c in chunks},
            "n_chunks": len(chunks), "vectordb_backend": "in-memory",
            "embedder": emb}


class TestWriter:
    def test_passthrough_strips(self) -> None:
        g = HyDEGenerator(generate_fn=lambda q: "  hypo passage  ")
        assert g.write("q") == "hypo passage"

    def test_failure_returns_empty(self) -> None:
        def boom(q):
            raise RuntimeError("LLM down")
        assert HyDEGenerator(generate_fn=boom).write("q") == ""

    def test_empty_response_returns_empty(self) -> None:
        assert HyDEGenerator(generate_fn=lambda q: "   ").write("q") == ""

    def test_vertex_path_needs_project(self) -> None:
        with pytest.raises(RuntimeError):
            HyDEGenerator(project_id="")


class TestFuse:
    def test_empty_hyde_returns_base_untouched(self) -> None:
        b = _bundle()
        from finrag.retrieval import retrieve_with_strategy

        base = retrieve_with_strategy(b, "Apple net sales", top_k=2)
        fused = hyde_fuse(b, "Apple net sales", top_k=2, hyde_text="",
                          base_hits=base)
        assert [c.chunk_id for c, _ in fused] == [c.chunk_id for c, _ in base]

    def test_hyde_side_can_promote(self) -> None:
        # HyDE prose about Azure should pull the Azure chunk into top-2
        # even when the original query ranks it lower.
        b = _bundle()
        from finrag.retrieval import retrieve_with_strategy

        base = retrieve_with_strategy(b, "Apple net sales", top_k=4)
        fused = hyde_fuse(b, "Apple net sales", top_k=2,
                          hyde_text="Microsoft Azure cloud revenue growth",
                          base_hits=base)
        ids = [c.chunk_id for c, _ in fused]
        assert len(ids) == len(set(ids)) == 2
        assert "c2" in ids

    def test_deterministic(self) -> None:
        b = _bundle()
        from finrag.retrieval import retrieve_with_strategy

        base = retrieve_with_strategy(b, "revenue", top_k=4)
        once = [c.chunk_id for c, _ in hyde_fuse(
            b, "revenue", top_k=3, hyde_text="sales income growth", base_hits=base)]
        twice = [c.chunk_id for c, _ in hyde_fuse(
            b, "revenue", top_k=3, hyde_text="sales income growth", base_hits=base)]
        assert once == twice

    def test_retrieve_wrapper_without_base(self) -> None:
        b = _bundle()
        hits = hyde_retrieve(b, "Apple net sales", top_k=2,
                             hyde_text="Apple iPhone sales revenue")
        assert len(hits) == 2


class TestFactory:
    def test_no_project_raises(self, monkeypatch) -> None:
        from finrag.config import get_settings

        monkeypatch.setenv("GCP_PROJECT_ID", "")
        get_settings.cache_clear()
        try:
            with pytest.raises(RuntimeError):
                get_hyde_generator()
        finally:
            get_settings.cache_clear()
