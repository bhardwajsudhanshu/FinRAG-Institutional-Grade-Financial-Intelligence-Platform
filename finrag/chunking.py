"""Naive fixed-size chunker with overlap (exp_001 baseline).

The strategy: slide a window of `chunk_size` tokens with `overlap` overlap
across the text. Each chunk is identified by `(filing_id, chunk_index)`.

This is the **floor** — every other chunker in Phase 2 must beat this on
the same eval set. No fancy paragraph or sentence respect; just raw tokens.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable

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
                        "chunker": "naive",
                    },
                )
            )
    return chunks


# --- exp_002: Recursive character chunker -----------------------------------
#
# LangChain's RecursiveCharacterTextSplitter tries a list of separators in
# order, recursing on the longest one first. The default list is:
#   ["\n\n", "\n", " ", ""]
# which means: prefer paragraph splits, fall back to line splits, then
# word splits, then character splits. This produces chunks that respect
# document structure much better than the naive fixed-size window.
#
# We use the *character-length* version (not token-length) because
# LangChain's API measures chunk_size in characters, and converting
# to tokens per call is non-trivial. The trade-off: a "1000-char"
# chunk is ~250 tokens, so the 1500-char default maps to ~375 tokens.
# For this project we use chunk_size=2000 (~500 tokens) and
# chunk_overlap=200 (~50 tokens), matching the exp_001 baseline's
# 512/50 token budget as closely as we can without bringing in a
# full token-counting wrapper.

_RECURSIVE_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def recursive_chunk_text(
    text: str,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> list[str]:
    """Split `text` recursively on paragraph/line/sentence boundaries.

    Equivalent to LangChain's `RecursiveCharacterTextSplitter` but
    inlined so we don't pull in langchain-text-splitters for one call.

    `chunk_size` and `chunk_overlap` are in *characters*, not tokens
    (matches LangChain's API). The default 2000/200 is calibrated so
    that a 512-token exp_001 chunk and a 2000-char recursive chunk
    have roughly the same embedding cost.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be in [0, chunk_size)")

    chunks: list[str] = []
    _recursive_split(text, _RECURSIVE_SEPARATORS, chunk_size, chunk_overlap, chunks)
    return [c for c in chunks if c.strip()]


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
    out: list[str],
) -> None:
    """In-place recursive splitter. Appends chunks to `out`."""
    if len(text) <= chunk_size:
        if text.strip():
            out.append(text)
        return

    # Pick the first separator that actually appears in `text`. The empty
    # string is the final fallback (split character-by-character).
    sep = ""
    for s in separators:
        if s and s in text:
            sep = s
            break

    if sep == "":
        # Fallback: hard slice. (Shouldn't normally trigger with the
        # default separator list, since " " is always present.)
        for i in range(0, len(text), chunk_size - chunk_overlap):
            out.append(text[i : i + chunk_size])
        return

    # Split on this separator, recurse on pieces that are still too big.
    pieces = text.split(sep)
    current = ""
    for piece in pieces:
        # candidate = current + sep + piece (if current non-empty)
        candidate = (current + sep + piece) if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            # Flush current (if it fits) and recurse on piece
            if current and len(current) <= chunk_size:
                out.append(current)
            elif current:
                # current itself is too big — recurse on it
                _recursive_split(current, _RECURSIVE_SEPARATORS[1:], chunk_size, chunk_overlap, out)
            current = piece
            if len(current) > chunk_size:
                # Recurse on the still-too-big piece with the next separator
                _recursive_split(current, _RECURSIVE_SEPARATORS[1:], chunk_size, chunk_overlap, out)
                current = ""
    if current.strip():
        out.append(current)


def chunk_sections_recursive(
    sections: list,
    ticker: str,
    filing_date: str,
    fiscal_year: int,
    accession_number: str,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> list[Chunk]:
    """Chunk a parsed 10-K's sections with the recursive splitter (exp_002).

    Same per-chunk metadata as `chunk_sections`, so the rest of the
    pipeline (embed, retrieve, RAGAS judge) doesn't know which chunker
    produced the chunks.
    """
    chunks: list[Chunk] = []
    for sec in sections:
        if not sec.text.strip():
            continue
        sub = recursive_chunk_text(
            sec.text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
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
                        "chunker": "recursive",
                    },
                )
            )
    return chunks


# --- exp_003: Semantic chunker ------------------------------------------------
#
# Sentence-level embedding-distance splits. Sentences with similar meaning
# stay in one chunk; a large cosine distance between consecutive sentences
# forces a breakpoint. Within each semantic region we still respect the
# max-tokens budget (same 512/50 as exp_001) so embedding cost is comparable.
#
# Cost note: chunking itself embeds every sentence once (via get_embedder),
# in addition to the later per-chunk embed in build_index. On Vertex this
# roughly doubles the embed bill for the run (~$0.025/M tokens x2).
# On mock backend it is free and deterministic.

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on [.?!]+whitespace or blank lines."""
    parts = _SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _cosine_distance(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    dot = sum(x * y for x, y in zip(a, b, strict=False)) / (na * nb)
    return max(0.0, min(2.0, 1.0 - dot))


def _percentile(data: list[float], p: float) -> float:
    """Linear-interpolated percentile (no numpy dependency)."""
    if not data:
        return 0.0
    s = sorted(data)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def semantic_chunk_text(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    threshold_percentile: float = 95.0,
    embed_fn=None,  # Callable[[list[str]], list[list[float]]] — injectable for tests
    encoding_name: str = "cl100k_base",
) -> list[str]:
    """Split `text` at semantic breakpoints (embedding distance spikes).

    Steps: sentences → embed → consecutive distances → breakpoint where
    distance >= P95 → greedily pack sentences up to `max_tokens`, cutting
    early at breakpoints. Single oversized sentences fall back to
    `naive_chunk_text`. Overlap is 1 trailing sentence carried forward
    (approximates the 50-token overlap budget without re-tokenizing).
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be > 0")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be in [0, max_tokens)")
    if not text.strip():
        return []
    sentences = _split_sentences(text)
    if not sentences:
        return []
    if len(sentences) == 1:
        enc = tiktoken.get_encoding(encoding_name)
        if len(_tokenize(sentences[0], enc)) <= max_tokens:
            return sentences
        return naive_chunk_text(
            sentences[0], chunk_size=max_tokens, overlap=overlap_tokens,
            encoding_name=encoding_name,
        )

    if embed_fn is None:
        from finrag.embeddings import get_embedder  # lazy: keeps chunking import-light

        embedder = get_embedder()
        vectors = embedder.embed_batch(sentences)
    else:
        vectors = embed_fn(sentences)

    distances = [_cosine_distance(vectors[i], vectors[i + 1]) for i in range(len(vectors) - 1)]
    threshold = _percentile(distances, threshold_percentile)
    breakpoints = {i + 1 for i, d in enumerate(distances) if d >= threshold}

    enc = tiktoken.get_encoding(encoding_name)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for idx, sent in enumerate(sentences):
        sent_tokens = len(_tokenize(sent, enc))
        if sent_tokens > max_tokens:
            # Flush current, then hard-split the monster sentence.
            if current:
                chunks.append(" ".join(current))
                current, current_tokens = [], 0
            chunks.extend(
                naive_chunk_text(
                    sent, chunk_size=max_tokens, overlap=overlap_tokens,
                    encoding_name=encoding_name,
                )
            )
            continue
        # Cut before this sentence if it starts a semantic region (and we
        # already hold something) or if adding it would bust the budget.
        if idx in breakpoints and current:
            chunks.append(" ".join(current))
            # Sentence overlap: carry last sentence forward (≈50-token budget).
            current = [current[-1]] if current else []
            current_tokens = len(_tokenize(" ".join(current), enc)) if current else 0
        if current_tokens + sent_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            current = [current[-1]] if current else []
            current_tokens = len(_tokenize(" ".join(current), enc)) if current else 0
        current.append(sent)
        current_tokens += sent_tokens
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if c.strip()]


def chunk_sections_semantic(
    sections: list,
    ticker: str,
    filing_date: str,
    fiscal_year: int,
    accession_number: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    threshold_percentile: float = 95.0,
    embed_fn=None,
) -> list[Chunk]:
    """Chunk a parsed 10-K's sections with the semantic splitter (exp_003).

    Same per-chunk metadata as naive/recursive plus `chunker="semantic"`.
    """
    chunks: list[Chunk] = []
    for sec in sections:
        if not sec.text.strip():
            continue
        sub = semantic_chunk_text(
            sec.text,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            threshold_percentile=threshold_percentile,
            embed_fn=embed_fn,
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
                        "chunker": "semantic",
                        "semantic_threshold_p": threshold_percentile,
                    },
                )
            )
    return chunks


# --- Chunker dispatch --------------------------------------------------------

# Map a `chunker_strategy` setting to a chunker function. The default
# `naive` is the exp_001 baseline; the rest are added by later experiments.
CHUNKER_DISPATCH: dict[str, Callable[..., list[Chunk]]] = {
    "naive": chunk_sections,
    "recursive": chunk_sections_recursive,
    "semantic": chunk_sections_semantic,
}


def chunk_sections_by_strategy(strategy: str, sections: list, **kwargs) -> list[Chunk]:
    """Dispatch to the chunker named by `strategy`. Raises KeyError on
    unknown strategy so misconfiguration is loud, not silent."""
    if strategy not in CHUNKER_DISPATCH:
        raise KeyError(
            f"Unknown chunker strategy {strategy!r}. "
            f"Valid options: {sorted(CHUNKER_DISPATCH.keys())}"
        )
    return CHUNKER_DISPATCH[strategy](sections, **kwargs)
