"""Unit tests for BM25 + hybrid RRF retrieval (Phase 3, ADR-004, exp_020/021).

These run WITHOUT calling Vertex or loading any filings. All retrieval
here is local: dense uses a stub, BM25 uses rank-bm25 on real text.

Critical properties:
- BM25 tokenizer is deterministic (lowercase alphanumerics).
- BM25 returns exact lexical matches first (numbers, tickers, names).
- Empty index / top_k<=0 returns [] instead of crashing.
- RRF fuses ranks correctly (shared #1 outranks single-list #1s).
- Strategy dispatcher routes dense/bm25/hybrid and rejects unknowns loudly.
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
from finrag.retrieval import (
    BM25Index,
    build_bm25_index,
    reciprocal_rank_fusion,
    tokenize_for_bm25,
)


def _mkchunk(cid: str, text: str) -> Chunk:
    return Chunk(chunk_id=cid, text=text, metadata={"section_id": "item_7"})


@pytest.fixture()
def corpus() -> list[Chunk]:
    return [
        _mkchunk("AAPL_item7::0000", "Apple net sales were $383.3 billion in fiscal 2023."),
        _mkchunk("AAPL_item7::0001", "Gross margin was 37.6 percent driven by Services mix."),
        _mkchunk("MSFT_item7::0000", "Microsoft Azure revenue grew 30 percent year over year."),
    ]


# --- tokenizer ---------------------------------------------------------------


def test_tokenize_lowercases_and_drops_punctuation() -> None:
    assert tokenize_for_bm25("Item 1A. Risk Factors!") == ["item", "1a", "risk", "factors"]


def test_tokenize_keeps_numbers() -> None:
    assert "383" in tokenize_for_bm25("$383.3 billion")


# --- BM25Index ---------------------------------------------------------------


def test_bm25_empty_index_returns_empty() -> None:
    assert BM25Index([]).query("anything", top_k=5) == []


def test_bm25_top_k_zero_returns_empty(corpus: list[Chunk]) -> None:
    assert BM25Index(corpus).query("Apple", top_k=0) == []


def test_bm25_exact_number_query_returns_right_chunk(corpus: list[Chunk]) -> None:
    hits = BM25Index(corpus).query("What was $383.3 billion?", top_k=1)
    assert len(hits) == 1
    assert hits[0][0].chunk_id == "AAPL_item7::0000"


def test_bm25_company_name_query_returns_right_chunk(corpus: list[Chunk]) -> None:
    hits = BM25Index(corpus).query("How did Microsoft Azure perform?", top_k=1)
    assert hits[0][0].chunk_id == "MSFT_item7::0000"


def test_bm25_len_matches_corpus(corpus: list[Chunk]) -> None:
    assert len(BM25Index(corpus)) == 3


def test_build_bm25_index_returns_index(corpus: list[Chunk]) -> None:
    idx = build_bm25_index(corpus)
    assert isinstance(idx, BM25Index)
    assert len(idx) == 3


# --- RRF ---------------------------------------------------------------------


def test_rrf_shared_top_outranks_single_list_tops() -> None:
    # d1 is #1 in both lists; d2/d3 each top one list. d1 must win.
    fused = reciprocal_rank_fusion([["d1", "d2"], ["d1", "d3"]], rrf_k=60)
    assert fused[0][0] == "d1"
    assert len(fused) == 3


def test_rrf_single_list_preserves_order_and_scores() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"]], rrf_k=60)
    assert [cid for cid, _ in fused] == ["a", "b", "c"]
    assert abs(fused[0][1] - 1 / 61) < 1e-9
    assert abs(fused[1][1] - 1 / 62) < 1e-9


def test_rrf_empty_input_returns_empty() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


# --- dispatcher --------------------------------------------------------------


def test_retrieve_with_strategy_rejects_unknown(corpus: list[Chunk]) -> None:
    from finrag.retrieval import retrieve_with_strategy

    bundle = {"strategy": "does_not_exist", "dense": None, "bm25": build_bm25_index(corpus),
              "chunks_by_id": {c.chunk_id: c for c in corpus}}
    with pytest.raises(ValueError):
        retrieve_with_strategy(bundle, "Apple revenue", top_k=5)


def test_retrieve_with_strategy_bm25_needs_no_dense(corpus: list[Chunk]) -> None:
    from finrag.retrieval import retrieve_with_strategy

    bundle = {"strategy": "bm25", "dense": None, "bm25": build_bm25_index(corpus),
              "chunks_by_id": {c.chunk_id: c for c in corpus}}
    hits = retrieve_with_strategy(bundle, "Microsoft Azure revenue", top_k=1)
    assert hits[0][0].chunk_id == "MSFT_item7::0000"
