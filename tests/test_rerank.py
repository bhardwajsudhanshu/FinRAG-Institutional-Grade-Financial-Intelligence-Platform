"""Unit tests for finrag/rerank.py (Phase 5, ADR-006, exp_030).

Offline: Flash scoring is injected via `score_fn` fakes — no Vertex.
Covers ordering, truncation, tie-breaks, unscored sinking, factories.
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
from finrag.rerank import FlashPointwiseReranker, NoopReranker, get_reranker


def _mk(cid: str, score: float = 0.5) -> tuple[Chunk, float]:
    return (Chunk(chunk_id=cid, text=f"text of {cid}", metadata={}), score)


class TestNoop:
    def test_passthrough_truncates(self) -> None:
        items = [_mk("a"), _mk("b"), _mk("c")]
        assert [c.chunk_id for c, _ in NoopReranker().rerank("q", items, top_k=2)] == ["a", "b"]

    def test_empty_in_empty_out(self) -> None:
        assert NoopReranker().rerank("q", [], top_k=5) == []


class TestFlashPointwise:
    def test_orders_by_score(self) -> None:
        scores = {"a": 2.0, "b": 9.0, "c": 5.0}
        r = FlashPointwiseReranker(score_fn=lambda q, t: scores[t.split()[-1]])
        items = [_mk("a", 0.9), _mk("b", 0.1), _mk("c", 0.5)]
        got = [c.chunk_id for c, _ in r.rerank("q", items, top_k=3)]
        assert got == ["b", "c", "a"]

    def test_ties_break_by_retrieval_score_then_rank(self) -> None:
        r = FlashPointwiseReranker(score_fn=lambda q, t: 7.0)
        items = [_mk("a", 0.2), _mk("b", 0.8), _mk("c", 0.5)]
        got = [c.chunk_id for c, _ in r.rerank("q", items, top_k=3)]
        assert got == ["b", "c", "a"]

    def test_unscored_sink_in_order(self) -> None:
        def fn(q, t):
            return None if "b" in t else 8.0
        r = FlashPointwiseReranker(score_fn=fn)
        items = [_mk("a", 0.1), _mk("b", 0.9), _mk("c", 0.2)]
        # a and c tie at 8.0 -> higher retrieval score (c, 0.2) wins the tie;
        # unscored b sinks last regardless of its 0.9 retrieval score.
        got = [c.chunk_id for c, _ in r.rerank("q", items, top_k=3)]
        assert got == ["c", "a", "b"]

    def test_scorer_exception_sinks(self) -> None:
        def fn(q, t):
            raise RuntimeError("LLM down")
        r = FlashPointwiseReranker(score_fn=fn)
        items = [_mk("a", 0.3), _mk("b", 0.7)]
        got = [c.chunk_id for c, _ in r.rerank("q", items, top_k=2)]
        assert got == ["b", "a"]

    def test_output_keeps_retrieval_scores(self) -> None:
        r = FlashPointwiseReranker(score_fn=lambda q, t: 10.0 if "b" in t else 0.0)
        items = [_mk("a", 0.3), _mk("b", 0.7)]
        got = r.rerank("q", items, top_k=2)
        assert [(c.chunk_id, s) for c, s in got] == [("b", 0.7), ("a", 0.3)]

    def test_truncates_to_top_k(self) -> None:
        r = FlashPointwiseReranker(score_fn=lambda q, t: 5.0)
        items = [_mk(f"c{i}", 0.1 * i) for i in range(10)]
        assert len(r.rerank("q", items, top_k=5)) == 5

    def test_vertex_path_needs_project(self) -> None:
        with pytest.raises(RuntimeError):
            FlashPointwiseReranker(project_id="")

    def test_model_id_labels_scorer(self) -> None:
        r = FlashPointwiseReranker(score_fn=lambda q, t: 1.0)
        assert "rerank" in r.model_id


class TestFactory:
    def test_unknown_backend_rejected(self, monkeypatch) -> None:
        from finrag.config import get_settings

        monkeypatch.setenv("RERANK_BACKEND", "does_not_exist")
        get_settings.cache_clear()
        try:
            with pytest.raises(ValueError):
                get_reranker()
        finally:
            get_settings.cache_clear()

    def test_none_backend_is_noop(self, monkeypatch) -> None:
        from finrag.config import get_settings

        monkeypatch.setenv("RERANK_BACKEND", "none")
        get_settings.cache_clear()
        try:
            assert isinstance(get_reranker(), NoopReranker)
        finally:
            get_settings.cache_clear()
