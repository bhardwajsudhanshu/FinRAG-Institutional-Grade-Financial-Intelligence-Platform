"""Tests for finrag/router.py (STEP_046). Fully offline, synthetic tables."""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from finrag.router import route_question, score_routing


class TestRouteQuestion:
    def test_out_of_scope_goes_lexical(self) -> None:
        assert route_question("Anything at all?", "out-of-scope") == "bm25"
        assert route_question("Anything at all?", "OUT-OF-SCOPE ") == "bm25"

    def test_item_and_section_anchors_go_lexical(self) -> None:
        assert route_question("What does item 1a list as risk?", "section") == "bm25"
        assert route_question("Summarize the section on revenue", "section") == "bm25"

    def test_short_lookups_go_lexical(self) -> None:
        assert route_question("Apple FY2023 revenue?", "lookup") == "bm25"

    def test_default_is_hybrid(self) -> None:
        assert route_question(
            "What does Apple's model estimate as the maximum potential one-day loss?",
            "section") == "hybrid"

    def test_oos_beats_anchor_rules(self) -> None:
        # qa_type branch is first — oos with an item ref still goes bm25
        # (same destination here; the ordering matters once rules diverge).
        assert route_question("item 7a unrelated?", "out-of-scope") == "bm25"


def _table() -> dict:
    return {
        "q1": {"dense": {"hit": True, "cite": True},
               "bm25": {"hit": False, "cite": False},
               "hybrid": {"hit": True, "cite": False}},
        "q2": {"dense": {"hit": False, "cite": False},
               "bm25": {"hit": True, "cite": True},
               "hybrid": {"hit": False, "cite": False}},
    }


class TestScoreRouting:
    def test_rates_and_oracle(self) -> None:
        r = score_routing(_table(), {"q1": "hybrid", "q2": "bm25"})
        assert r["n"] == 2
        assert r["hit_rate"] == 1.0
        assert r["cite_rate"] == 0.5
        assert r["oracle_hit_rate"] == 1.0
        assert r["oracle_cite_rate"] == 1.0

    def test_suboptimal_routing_scores_below_oracle(self) -> None:
        r = score_routing(_table(), {"q1": "bm25", "q2": "hybrid"})
        assert r["hit_rate"] == 0.0
        assert r["oracle_hit_rate"] == 1.0

    def test_unknown_qid_raises(self) -> None:
        with pytest.raises(KeyError):
            score_routing(_table(), {"q1": "hybrid", "qX": "bm25"})

    def test_unknown_strategy_raises(self) -> None:
        with pytest.raises(KeyError):
            score_routing(_table(), {"q1": "rerank", "q2": "bm25"})

    def test_empty_decisions_raise(self) -> None:
        with pytest.raises(ValueError):
            score_routing(_table(), {})
