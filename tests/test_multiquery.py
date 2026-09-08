"""Unit tests for finrag/multiquery.py (STEP_034, exp_043). Offline.

Flash paraphrasing is injected via `generate_fn` fakes; retrieval runs on
MockEmbedder. Covers expansion hygiene, single-query equivalence, fusion
recall (paraphrase-only hits surface), determinism, and factories.
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
from finrag.multiquery import QueryExpander, get_expander, multi_query_retrieve


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


class TestExpand:
    def test_passthrough_strips_and_caps(self) -> None:
        ex = QueryExpander(generate_fn=lambda q, n: ["  a  ", "", "b", "c"])
        assert ex.expand("q", n=2) == ["a", "b"]

    def test_failure_falls_back_to_empty(self) -> None:
        def boom(q, n):
            raise RuntimeError("LLM down")
        assert QueryExpander(generate_fn=boom).expand("q") == []

    def test_vertex_path_needs_project(self) -> None:
        with pytest.raises(RuntimeError):
            QueryExpander(project_id="")


class TestFuse:
    def test_empty_paraphrases_is_single_query(self) -> None:
        from finrag.retrieval import retrieve_with_strategy

        b = _bundle()
        direct = [c.chunk_id for c, _ in retrieve_with_strategy(b, "Apple net sales", top_k=2)]
        fused = [c.chunk_id for c, _ in multi_query_retrieve(b, "Apple net sales", top_k=2, paraphrases=[])]
        assert fused == direct

    def test_paraphrase_only_hit_surfaces(self) -> None:
        # Paraphrase mentions Azure; the fused top-3 must contain the Azure
        # chunk (lexical overlap guarantees it under any sane embedder).
        b = _bundle()
        fused = {c.chunk_id for c, _ in multi_query_retrieve(
            b, "Apple net sales", top_k=3, paraphrases=["Microsoft Azure cloud growth"])}
        assert "c2" in fused

    def test_dedup_and_top_k(self) -> None:
        b = _bundle()
        hits = multi_query_retrieve(b, "revenue", top_k=2,
                                    paraphrases=["revenue income", "revenue sales"])
        ids = [c.chunk_id for c, _ in hits]
        assert len(ids) == len(set(ids)) == 2

    def test_deterministic(self) -> None:
        b = _bundle()
        once = [c.chunk_id for c, _ in multi_query_retrieve(
            b, "revenue", top_k=3, paraphrases=["sales income", "margin profit"])]
        twice = [c.chunk_id for c, _ in multi_query_retrieve(
            b, "revenue", top_k=3, paraphrases=["sales income", "margin profit"])]
        assert once == twice


class TestFactory:
    def test_no_project_raises(self, monkeypatch) -> None:
        from finrag.config import get_settings

        monkeypatch.setenv("GCP_PROJECT_ID", "")
        get_settings.cache_clear()
        try:
            with pytest.raises(RuntimeError):
                get_expander()
        finally:
            get_settings.cache_clear()
