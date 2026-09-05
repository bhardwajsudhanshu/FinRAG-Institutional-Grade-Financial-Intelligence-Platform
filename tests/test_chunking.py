"""Unit tests for the chunker dispatch (naive + recursive, exp_001 + exp_002).

These run WITHOUT calling Vertex or loading any filings. We feed small
synthetic sections and assert:

- dispatch picks the right chunker
- recursive respects paragraph boundaries (chunks end at "\n\n")
- chunks from each strategy carry the right `chunker` metadata
- unknown strategy raises KeyError loudly
"""

from __future__ import annotations

import sys
from pathlib import Path

# tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from finrag.chunking import (
    CHUNKER_DISPATCH,
    Chunk,
    chunk_sections,
    chunk_sections_by_strategy,
    chunk_sections_recursive,
    naive_chunk_text,
    recursive_chunk_text,
)


# --- ParsedSection stand-in --------------------------------------------------


class _FakeSection:
    """Minimal duck-typed stand-in for finrag.data.parse_sections.ParsedSection."""

    def __init__(self, section_id: str, title: str, text: str) -> None:
        self.section_id = section_id
        self.title = title
        self.text = text


# --- naive_chunk_text --------------------------------------------------------


def test_naive_chunk_text_empty_returns_empty_list() -> None:
    assert naive_chunk_text("") == []


def test_naive_chunk_text_short_returns_single_chunk() -> None:
    out = naive_chunk_text("Hello, world.", chunk_size=512, overlap=50)
    assert out == ["Hello, world."]


def test_naive_chunk_text_chunk_size_must_be_positive() -> None:
    with pytest.raises(ValueError):
        naive_chunk_text("hi", chunk_size=0)


def test_naive_chunk_text_overlap_must_be_lt_chunk_size() -> None:
    with pytest.raises(ValueError):
        naive_chunk_text("hi", chunk_size=100, overlap=100)


# --- recursive_chunk_text ----------------------------------------------------


def test_recursive_chunk_text_empty_returns_empty_list() -> None:
    assert recursive_chunk_text("") == []


def test_recursive_chunk_text_short_returns_single_chunk() -> None:
    text = "Short paragraph."
    out = recursive_chunk_text(text, chunk_size=2000, chunk_overlap=200)
    assert out == [text]


def test_recursive_chunk_text_keeps_paragraphs_together_when_small() -> None:
    # 3 short paragraphs; well under chunk_size, so should be one chunk
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    out = recursive_chunk_text(text, chunk_size=2000, chunk_overlap=200)
    assert len(out) == 1
    assert "First" in out[0]
    assert "Third" in out[0]


def test_recursive_chunk_text_splits_at_paragraph_boundary_when_too_big() -> None:
    # Two paragraphs; each is just over half the chunk budget. Should split
    # on the "\n\n" separator rather than mid-paragraph.
    para1 = "Alpha " * 300  # ~1500 chars
    para2 = "Beta " * 300
    text = f"{para1}\n\n{para2}"
    out = recursive_chunk_text(text, chunk_size=1600, chunk_overlap=200)
    # We expect at least 2 chunks (one for each paragraph); the second
    # paragraph should NOT be split mid-sentence.
    assert len(out) >= 2
    # No chunk should contain a mix of "Alpha" and "Beta" tokens
    # (this is the property we care about: paragraph respect).
    for chunk in out:
        has_alpha = "Alpha" in chunk
        has_beta = "Beta" in chunk
        # Allow a chunk to contain both ONLY if it's the overlap region;
        # the property we really want is that the first chunk ends
        # cleanly at or near the paragraph boundary.
        if has_alpha and has_beta and chunk != out[-1]:
            # Mid-chunk cross-paragraph blend before the boundary — not OK
            assert "Alpha" not in chunk.split("\n\n")[0] or "Beta" not in chunk.split("\n\n")[-1]


def test_recursive_chunk_text_chunk_size_must_be_positive() -> None:
    with pytest.raises(ValueError):
        recursive_chunk_text("hi", chunk_size=0)


def test_recursive_chunk_text_overlap_must_be_lt_chunk_size() -> None:
    with pytest.raises(ValueError):
        recursive_chunk_text("hi", chunk_size=100, chunk_overlap=100)


# --- chunk_sections / chunk_sections_recursive ------------------------------


def test_chunk_sections_sets_chunker_metadata_naive() -> None:
    sec = _FakeSection("item_7", "MD&A", "Some MD&A text " * 200)
    out = chunk_sections([sec], ticker="AAPL", filing_date="2025-10-31",
                         fiscal_year=2025, accession_number="0000320193-25-000001")
    assert out
    assert all(c.metadata["chunker"] == "naive" for c in out)


def test_chunk_sections_recursive_sets_chunker_metadata() -> None:
    sec = _FakeSection("item_7", "MD&A", "Some MD&A text " * 200)
    out = chunk_sections_recursive([sec], ticker="AAPL", filing_date="2025-10-31",
                                   fiscal_year=2025,
                                   accession_number="0000320193-25-000001")
    assert out
    assert all(c.metadata["chunker"] == "recursive" for c in out)


def test_chunk_sections_skips_empty_sections() -> None:
    sec1 = _FakeSection("item_1", "Business", "")
    sec2 = _FakeSection("item_7", "MD&A", "Real content " * 200)
    out = chunk_sections([sec1, sec2], ticker="AAPL", filing_date="2025-10-31",
                         fiscal_year=2025, accession_number="0000320193-25-000001")
    assert all(c.metadata["section_id"] == "item_7" for c in out)


# --- chunker dispatch -------------------------------------------------------


def test_chunker_dispatch_has_naive_and_recursive() -> None:
    assert "naive" in CHUNKER_DISPATCH
    assert "recursive" in CHUNKER_DISPATCH


def test_chunk_sections_by_strategy_dispatches_correctly() -> None:
    sec = _FakeSection("item_7", "MD&A", "Real content " * 200)
    naive_out = chunk_sections_by_strategy(
        "naive", [sec], ticker="AAPL", filing_date="2025-10-31",
        fiscal_year=2025, accession_number="0000320193-25-000001",
    )
    rec_out = chunk_sections_by_strategy(
        "recursive", [sec], ticker="AAPL", filing_date="2025-10-31",
        fiscal_year=2025, accession_number="0000320193-25-000001",
    )
    assert all(c.metadata["chunker"] == "naive" for c in naive_out)
    assert all(c.metadata["chunker"] == "recursive" for c in rec_out)


def test_chunk_sections_by_strategy_unknown_raises() -> None:
    sec = _FakeSection("item_7", "MD&A", "Real content " * 200)
    with pytest.raises(KeyError):
        chunk_sections_by_strategy(
            "does_not_exist", [sec], ticker="AAPL", filing_date="2025-10-31",
            fiscal_year=2025, accession_number="0000320193-25-000001",
        )
