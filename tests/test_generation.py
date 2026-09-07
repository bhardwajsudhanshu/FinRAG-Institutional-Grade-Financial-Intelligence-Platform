"""Unit tests for finrag/generation.py helpers (STEP_014).

No Vertex calls: Vertex response shapes are stubbed with duck-typed
fakes. Covers the exp_020 q_0053 failure (multi-part `.text` raising)
plus MockGenerator's offline contract.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from finrag.generation import Citation, MockGenerator, _response_text


class _Part:
    def __init__(self, text: str | None) -> None:
        self.text = text


class _Content:
    def __init__(self, parts: list) -> None:
        self.parts = parts


class _Cand:
    def __init__(self, parts: list) -> None:
        self.content = _Content(parts)


class _RespSingle:
    text = "I cannot find this in the provided filings."
    candidates: ClassVar[list] = []


class _RespMulti:
    # Mirrors exp_020 q_0053: two identical refusal parts; SDK .text raises.
    candidates: ClassVar[list] = [_Cand([_Part("I cannot find this in the provided filings."),
                                         _Part("I cannot find this in the provided filings.")])]

    @property
    def text(self) -> str:
        raise ValueError("Multiple content parts are not supported.")


class _RespEmpty:
    candidates: ClassVar[list] = []

    @property
    def text(self) -> str:
        raise ValueError("No candidates.")


class _RespMixed:
    candidates: ClassVar[list] = [_Cand([_Part(None), _Part("real")])]

    @property
    def text(self) -> str:
        raise ValueError("Multiple content parts are not supported.")


class TestResponseText:
    def test_single_part_uses_dot_text(self) -> None:
        assert _response_text(_RespSingle()) == "I cannot find this in the provided filings."

    def test_multi_part_joins_texts(self) -> None:
        out = _response_text(_RespMulti())
        assert out.count("I cannot find this in the provided filings.") == 2

    def test_empty_response_returns_empty_string(self) -> None:
        assert _response_text(_RespEmpty()) == ""

    def test_none_text_parts_skipped(self) -> None:
        assert _response_text(_RespMixed()) == "real"


class TestMockGenerator:
    def test_empty_contexts_refuse(self) -> None:
        res = MockGenerator().generate("What was revenue?", [])
        assert "I cannot find this" in res.answer
        assert res.citations == []
        assert res.model == "mock-generator"

    def test_contexts_cited_with_scores(self) -> None:
        cites = [Citation(chunk_id="AAPL_x::0001", score=0.9, metadata={})]
        res = MockGenerator().generate("Q?", [("Some filing text here.", cites[0])])
        assert "[AAPL_x::0001]" in res.answer
        assert res.citations == cites
