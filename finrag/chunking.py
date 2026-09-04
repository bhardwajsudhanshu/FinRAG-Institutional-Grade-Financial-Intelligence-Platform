"""Naive fixed-size chunker with overlap (exp_001 baseline).

The strategy: slide a window of `chunk_size` tokens with `overlap` overlap
across the text. Each chunk is identified by `(filing_id, chunk_index)`.

This is the **floor** — every other chunker in Phase 2 must beat this on
the same eval set. No fancy paragraph or sentence respect; just raw tokens.
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from finrag.config import get_settings


@dataclass
class Chunk:
    """One chunk of text, ready to embed and index."""

    chunk_id: str           # e.g. "AAPL_2023-11-03_item_1a::0001"
    text: str
    metadata: dict          # ticker, filing_date, section, fiscal_year, etc.

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            **self.metadata,
        }


def _tokenize(text: str, encoding) -> list[int]:
    return encoding.encode(text, disallowed_special=())


def _detokenize(tokens: list[int], encoding) -> str:
    return encoding.decode(tokens)


def naive_chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
    encoding_name: str = "cl100k_base",
) -> list[str]:
    """Split `text` into overlapping token windows.

    Each returned string is at most `chunk_size` tokens long. The last chunk
    may be shorter.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")
    enc = tiktoken.get_encoding(encoding_name)
    tokens = _tokenize(text, enc)
    if not tokens:
        return []
    chunks: list[str] = []
    stride = chunk_size - overlap
    for start in range(0, len(tokens), stride):
        window = tokens[start : start + chunk_size]
        chunks.append(_detokenize(window, enc))
        if start + chunk_size >= len(tokens):
            break
    return chunks


def chunk_sections(
    sections: list,  # list[ParsedSection] — avoid circular import
    ticker: str,
    filing_date: str,
    fiscal_year: int,
    accession_number: str,
) -> list[Chunk]:
    """Chunk a parsed 10-K's sections. Returns a flat list of Chunks.

    Each chunk's `metadata` carries enough info to filter and cite it
    downstream (ticker, year, section, filing date, accession number).
    """
    settings = get_settings()
    chunks: list[Chunk] = []
    for sec in sections:
        if not sec.text.strip():
            continue
        sub = naive_chunk_text(
            sec.text,
            chunk_size=settings.chunk_size_tokens,
            overlap=settings.chunk_overlap_tokens,
        )
        for i, text in enumerate(sub):
            cid = f"{ticker}_{filing_date}_{sec.section_id}::{i:04d}"
            chunks.append(
                Chunk(
                    chunk_id=cid,
                    text=text,
                    metadata={
                        "ticker": ticker,
                        "filing_date": filing_date,
                        "fiscal_year": fiscal_year,
                        "accession_number": accession_number,
                        "section_id": sec.section_id,
                        "section_title": sec.title,
                        "chunk_index": i,
                    },
                )
            )
    return chunks
