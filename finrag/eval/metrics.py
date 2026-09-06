"""Custom retrieval metrics for FinRAG evals.

The locked `hit_at_5` and `citation_accuracy` columns in
`results/experiments.csv` measure whether the eval set's `source_chunk_id`
appears in the retrieved / cited chunk IDs. This is brittle: the eval set's
`source_chunk_id` was generated from the chunk IDs that existed *under the
naive chunker* (exp_001). When the chunker changes, the same paragraph
text gets a different chunk_id, and chunk_id-based hit metrics become a
measurement artifact rather than a property of retrieval.

To fix this without editing the frozen eval set, every Q&A record also
carries a `source_span` field — the exact substring of the source chunk
that supports the ground truth. This module provides the
chunker-agnostic, content-anchored match function we use to score
`hit_at_5_content` and `citation_accuracy_content` from exp_003 onward.

The matching strategy is whitespace-tolerant and case-insensitive, with
two fallbacks for very long spans (where the full span may straddle a
chunk boundary under paragraph-aware chunking):

1. Direct substring of the normalized span inside the normalized chunk
2. First 100 chars of the normalized span (covers tail-trimmed spans)
3. Last 100 chars of the normalized span (covers head-trimmed spans)

This is the same logic that has lived in
`tests/eval/generate_qa_pairs.py::_span_appears_in_chunk` since the
frozen v1 eval set was generated; we promote it here so the eval runner
and the Q&A generator share one canonical implementation.
"""

from __future__ import annotations

import re

# A regex pre-compiled at import time. Whitespace runs collapse to a
# single space, then we lowercase the whole string. This is the only
# normalization we need for fuzzy containment.
_WHITESPACE_RE = re.compile(r"\s+")

# Length of the head/tail probes used when the full span doesn't match
# directly. 100 chars is roughly one to two sentences and survives
# paragraph-aware chunking's tendency to split on the next separator.
_HEAD_PROBE = 100


def _normalize(text: str) -> str:
    """Collapse whitespace runs to a single space and lowercase.

    Examples:
        >>> _normalize("  Hello\\nWORLD\\t! ")
        'hello world !'
    """
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def span_appears_in_chunk(span: str, chunk_text: str) -> bool:
    """True iff `span` is found in `chunk_text` under fuzzy matching.

    Empty or whitespace-only `span` returns False (an empty anchor is not
    a useful match — and OOS Q's have an empty `source_span` by design).

    The match is whitespace-tolerant (multiple spaces / newlines / tabs
    are treated as one space) and case-insensitive. If the full normalized
    span is longer than ~100 chars, the first and last 100 chars are also
    tried as a fallback, which covers the common case where a span
    straddles a paragraph split introduced by paragraph-aware chunking.

    Args:
        span: The source substring from a Q&A record's `source_span` field.
        chunk_text: The text of a retrieved or cited chunk.

    Returns:
        True if any of the three probes (full, head, tail) is contained
        in the normalized chunk_text.
    """
    if not span or not chunk_text:
        return False

    n_span = _normalize(span)
    n_chunk = _normalize(chunk_text)
    if not n_span or not n_chunk:
        return False

    # 1) Direct contains — the common case.
    if n_span in n_chunk:
        return True

    # 2) & 3) Head / tail probes — only meaningful for long spans,
    # where a chunker split the source paragraph mid-sentence.
    if len(n_span) > _HEAD_PROBE:
        if n_span[:_HEAD_PROBE] in n_chunk:
            return True
        if n_span[-_HEAD_PROBE:] in n_chunk:
            return True

    return False
