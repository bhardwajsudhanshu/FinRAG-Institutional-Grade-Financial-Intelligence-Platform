"""Unit tests for parent-document retrieval (STEP_030, exp_041). Offline.

Covers: parents identical to naive chunks, child id/metadata shape,
validation, and the retrieve->map-to-parents dispatch (dedup, top_k,
unknown strategy still loud).
"""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from finrag.chunking import chunk_sections
from finrag.parentdoc import build_parent_child_chunks


class _FakeSection:
    def __init__(self, section_id: str, title: str, text: str) -> None:
        self.section_id = section_id
        self.title = title
        self.text = text


def _kwargs(**over):
    base = dict(ticker="AAPL", filing_date="2025-10-31", fiscal_year=2025,
                accession_number="0000320193-25-000001")
    base.update(over)
    return base


class TestBuild:
    def test_parents_identical_to_naive(self) -> None:
        secs = [_FakeSection("item_7", "MD&A", "Some MD&A text " * 200)]
        parents, _, _ = build_parent_child_chunks(secs, **_kwargs())
        expected = chunk_sections(secs, **_kwargs())
        assert [p.chunk_id for p in parents] == [c.chunk_id for c in expected]
        assert [p.text for p in parents] == [c.text for c in expected]

    def test_children_point_at_parents(self) -> None:
        secs = [_FakeSection("item_7", "MD&A", "Some MD&A text " * 200)]
        parents, children, mapping = build_parent_child_chunks(secs, **_kwargs())
        assert children
        parent_ids = {p.chunk_id for p in parents}
        for child in children:
            assert child.chunk_id.startswith(child.metadata["parent_id"] + ":c")
            assert child.metadata["parent_id"] in parent_ids
            assert child.metadata["chunker"] == "parent-doc"
            assert mapping[child.chunk_id] == child.metadata["parent_id"]

    def test_short_parent_yields_single_child(self) -> None:
        secs = [_FakeSection("item_7", "MD&A", "Short text.")]
        parents, children, _ = build_parent_child_chunks(secs, **_kwargs())
        assert len(parents) == 1
        assert len(children) == 1

    def test_empty_sections_skipped(self) -> None:
        secs = [_FakeSection("item_1", "Business", ""),
                _FakeSection("item_7", "MD&A", "Real content " * 200)]
        parents, children, mapping = build_parent_child_chunks(secs, **_kwargs())
        assert all(p.metadata["section_id"] == "item_7" for p in parents)
        assert all(mapping[c.chunk_id].endswith("item_7::0000") or "item_7" in mapping[c.chunk_id]
                   for c in children)

    def test_invalid_child_args_raise(self) -> None:
        secs = [_FakeSection("item_7", "MD&A", "text")]
        with pytest.raises(ValueError):
            build_parent_child_chunks(secs, **_kwargs(), child_size=0)
        with pytest.raises(ValueError):
            build_parent_child_chunks(secs, **_kwargs(), child_size=100, child_overlap=100)


class TestDispatch:
    def _bundle(self):
        from finrag.embeddings import MockEmbedder
        from finrag.retrieval import InMemoryIndex, retrieve_with_strategy

        secs = [_FakeSection("item_7", "MD&A",
                             "Apple net sales were $383.3B. Gross margin rose. " * 40)]
        parents, children, _ = build_parent_child_chunks(secs, **_kwargs())
        emb = MockEmbedder(dim=64)
        idx = InMemoryIndex()
        for c in children:
            idx.add(c, emb.embed(c.text))
        by_id = {p.chunk_id: p for p in parents}
        bundle = {"strategy": "parent-doc", "dense": idx, "bm25": None,
                  "chunks_by_id": by_id, "n_chunks": len(parents),
                  "n_child_chunks": len(children),
                  "vectordb_backend": "in-memory", "embedder": emb}
        return bundle, retrieve_with_strategy

    def test_child_hit_returns_parent(self) -> None:
        bundle, retrieve_with_strategy = self._bundle()
        hits = retrieve_with_strategy(bundle, "Apple net sales", top_k=2)
        assert hits
        assert all("::c" not in c.chunk_id for c, _ in hits)
        assert all(c.metadata["chunker"] == "naive" for c, _ in hits)

    def test_parents_deduplicated(self) -> None:
        bundle, retrieve_with_strategy = self._bundle()
        hits = retrieve_with_strategy(bundle, "Apple net sales margin", top_k=5)
        ids = [c.chunk_id for c, _ in hits]
        assert len(ids) == len(set(ids))

    def test_top_k_parents_respected(self) -> None:
        bundle, retrieve_with_strategy = self._bundle()
        hits = retrieve_with_strategy(bundle, "Apple", top_k=1)
        assert len(hits) <= 1


class TestHybridParent:
    """STEP_032: fuse in child space, generate from parents."""

    def _bundle(self):
        from finrag.embeddings import MockEmbedder
        from finrag.retrieval import InMemoryIndex, build_bm25_index

        secs = [_FakeSection("item_7", "MD&A",
                             "Apple net sales were $383.3B. Gross margin rose. " * 40)]
        parents, children, _ = build_parent_child_chunks(secs, **_kwargs())
        emb = MockEmbedder(dim=64)
        idx = InMemoryIndex()
        for c in children:
            idx.add(c, emb.embed(c.text))
        return {
            "strategy": "hybrid-parent", "dense": idx,
            "bm25": build_bm25_index(children),
            "chunks_by_id": {p.chunk_id: p for p in parents},
            "children_by_id": {c.chunk_id: c for c in children},
            "n_chunks": len(parents), "n_child_chunks": len(children),
            "vectordb_backend": "in-memory", "embedder": emb,
        }

    def test_returns_parents_not_children(self) -> None:
        from finrag.retrieval import retrieve_with_strategy

        hits = retrieve_with_strategy(self._bundle(), "Apple net sales", top_k=3)
        assert hits
        assert all("::c" not in c.chunk_id for c, _ in hits)
        assert len({c.chunk_id for c, _ in hits}) == len(hits)

    def test_unknown_child_ids_skipped(self) -> None:
        from finrag.retrieval import retrieve_with_strategy

        bundle = self._bundle()
        bundle["children_by_id"] = {}  # fused ids unresolvable -> no crash
        assert retrieve_with_strategy(bundle, "Apple net sales", top_k=3) == []
