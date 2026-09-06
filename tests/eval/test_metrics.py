"""Unit tests for finrag/eval/metrics.py:span_appears_in_chunk.

These tests pin the behavior the RAGAS runner relies on for the new
content-anchored `hit_at_5_content` and `citation_accuracy_content` metrics.

Critical properties:
- Direct substring match works (case-insensitive, whitespace-tolerant).
- Empty / whitespace-only spans return False (OOS Q's have no span).
- Empty chunk_text returns False.
- Long spans falling back to head/tail probes work.
- Spans that don't match the chunk at all return False.
- A span that's just the same case/different whitespace still matches.
"""

from __future__ import annotations

import pytest

from finrag.eval.metrics import normalize_source_span, span_appears_in_chunk


class TestDirectMatch:
    def test_simple_substring_match(self):
        assert span_appears_in_chunk(
            "Apple net sales were $383.3 billion",
            "Apple net sales were $383.3 billion in fiscal 2023.",
        )

    def test_case_insensitive(self):
        # Span is uppercase, chunk is mixed case -> still matches
        assert span_appears_in_chunk(
            "APPLE NET SALES",
            "apple net sales were $383.3B",
        )

    def test_whitespace_tolerant(self):
        # Span has multiple spaces and newlines; chunk has tabs -> still matches
        assert span_appears_in_chunk(
            "Apple\nnet   sales  were  $383.3B",
            "Apple\tnet sales were\t$383.3B in FY23",
        )

    def test_match_at_chunk_start(self):
        assert span_appears_in_chunk(
            "fiscal 2023 net sales",
            "fiscal 2023 net sales were $383.3B and operating income...",
        )

    def test_match_at_chunk_end(self):
        assert span_appears_in_chunk(
            "$383.3 billion in fiscal 2023",
            "Apple's total net sales were $383.3 billion in fiscal 2023",
        )


class TestHeadTailFallbacks:
    def test_long_span_head_matches(self):
        # Build a 200+ char span whose first 100 chars are a distinctive head
        # probe that the chunk contains, but whose tail the chunk does not have.
        head = (
            "Apple's total net sales for fiscal 2023 were $383.3 billion, "
            "representing a modest decline driven primarily by lower iPhone "
            "revenue and unfavorable foreign exchange movements across "
        )
        assert len(head) > 100
        tail = "emerging markets including Brazil India and Southeast Asia region"
        long_span = head + tail
        assert len(long_span) > 200

        # Chunk has the head probe (and a bit more) but the tail is cut off
        chunk = head + "developed markets."
        assert span_appears_in_chunk(long_span, chunk)

    def test_long_span_tail_matches(self):
        # Build a 200+ char span whose last 100 chars are a distinctive tail
        # probe that the chunk contains, but whose head the chunk does not have.
        # The tail must itself be > 100 chars so the last-100 probe is clean
        # (no missing head characters bleeding into the probe).
        head = "x" * 100  # 100 chars of x's (the missing head)
        tail = (
            " Segment results show that operating income for fiscal 2023 was "
            "$114.3 billion across all reporting segments combined"
        )
        long_span = head + tail
        assert len(long_span) > 200
        assert len(tail) > 100  # ensures the last-100 probe is the tail only

        # Chunk has only the tail (no leading x's)
        chunk = "Apple Inc. 10-K filing." + tail
        assert span_appears_in_chunk(long_span, chunk)

    def test_short_span_direct_match_works(self):
        # A short span that DOES appear in the chunk matches via direct contains
        assert span_appears_in_chunk(
            "operating income",
            "Apple's operating income was $114.3B in FY23.",
        )

    def test_short_span_no_match(self):
        # A short span that's not a substring of the chunk -> False
        # (we don't trigger head/tail probes for short spans)
        assert not span_appears_in_chunk(
            "this exact text is not in the chunk anywhere",
            "Apple net sales were $383.3B.",
        )


class TestEmptyInputs:
    def test_empty_span_returns_false(self):
        # Empty span (OOS Q's have no span) -> False, not True
        assert not span_appears_in_chunk("", "Apple net sales $383.3B")

    def test_whitespace_only_span_returns_false(self):
        assert not span_appears_in_chunk("   \n\t  ", "Apple net sales $383.3B")

    def test_empty_chunk_returns_false(self):
        assert not span_appears_in_chunk("Apple net sales", "")

    def test_whitespace_only_chunk_returns_false(self):
        assert not span_appears_in_chunk("Apple net sales", "   \n  ")

    def test_both_empty_returns_false(self):
        assert not span_appears_in_chunk("", "")


class TestNonMatch:
    def test_span_not_in_chunk(self):
        assert not span_appears_in_chunk(
            "Microsoft Azure revenue grew 30%",
            "Apple net sales were $383.3B in fiscal 2023.",
        )

    def test_partial_match_only_is_not_enough(self):
        # The head/tail probes must be exact, not "contains the keyword somewhere".
        # A 200+ char span with "keyword" in the middle should NOT match a chunk
        # that only contains the word "keyword" but not the full head/tail.
        head = "z" * 100  # 100 z's
        tail = "w" * 100  # 100 w's
        long_span = head + " keyword " + tail
        chunk = "Some text with the word keyword but not the surrounding z's and w's"
        assert not span_appears_in_chunk(long_span, chunk)


class TestRealisticContent:
    """Smoke tests with realistic 10-K-style text."""

    def test_financial_figure_with_comma_variants(self):
        # The Q&A generator may emit spans with or without commas;
        # the helper normalizes whitespace but not digits/punctuation.
        # So these should be exact: same punctuation must be present.
        chunk = "Apple reported net sales of $383,285 million in 2023."
        assert span_appears_in_chunk("$383,285 million", chunk)
        # Without the comma, it shouldn't match (we don't strip punctuation)
        assert not span_appears_in_chunk("$383285 million", chunk)

    def test_realistic_10k_paragraph(self):
        chunk = (
            "The Company's total net sales were $383.3 billion in fiscal 2023, "
            "compared to $394.3 billion in fiscal 2022. The decrease was driven "
            "primarily by lower iPhone revenue and unfavorable foreign exchange "
            "movements across emerging markets."
        )
        assert span_appears_in_chunk("$383.3 billion in fiscal 2023", chunk)
        assert span_appears_in_chunk("iPhone revenue", chunk)
        assert span_appears_in_chunk("foreign exchange movements", chunk)
        assert not span_appears_in_chunk("Microsoft Azure", chunk)


@pytest.mark.parametrize(
    "span,chunk,expected",
    [
        ("net sales $383.3B", "Apple net sales $383.3B in FY23", True),
        ("Microsoft", "Apple net sales $383.3B in FY23", False),
        ("", "Apple net sales $383.3B in FY23", False),
        ("net sales", "", False),
        ("NET SALES", "net sales $383.3B", True),
        ("net\nsales", "net sales $383.3B", True),
    ],
)
def test_parametrized(span, chunk, expected):
    assert span_appears_in_chunk(span, chunk) is expected


class TestNormalizeSourceSpan:
    """Pins the STEP_009 OOS-sentinel fix the runner relies on.

    The frozen v1 set stores the literal "<no relevant span>" string for
    OOS Q's. The runner's OOS branches test emptiness, so the sentinel
    must normalize to "" at read time (eval set itself stays frozen).
    """

    def test_none_returns_empty(self):
        assert normalize_source_span(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_source_span("") == ""

    def test_whitespace_only_returns_empty(self):
        assert normalize_source_span("   \n\t  ") == ""

    def test_sentinel_returns_empty(self):
        assert normalize_source_span("<no relevant span>") == ""

    def test_sentinel_with_padding_returns_empty(self):
        assert normalize_source_span("  <no relevant span>\n") == ""

    def test_real_span_passes_through_stripped(self):
        assert (
            normalize_source_span("  Apple net sales $383.3B  ")
            == "Apple net sales $383.3B"
        )

    def test_near_miss_sentinel_is_not_emptied(self):
        # Only the exact sentinel normalizes; anything else is a real span
        # (prevents silently dropping answer-bearing text on a typo).
        s = "<no relevantSpan>"
        assert normalize_source_span(s) == s
