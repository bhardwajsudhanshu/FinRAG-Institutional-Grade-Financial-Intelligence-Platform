"""Parse a 10-K filing into named sections.

The 10-K format is highly structured: Item 1, 1A, 7, 7A, 8, etc. We split on
the literal text "Item N. <Title>" with a regex.

Limitations:
- Real filings sometimes have multi-line item headers ("Item 1.\nBusiness")
- Some filings bury items in tables of contents
- A small percentage of filings won't parse cleanly — we track the parse
  rate so we know if our parser breaks.

For the smoke test (synthetic filing) this is robust. For real filings we'll
spot-check 5 random filings in Day 1 and iterate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

# The 10-K items we care about for RAG. Each pattern matches the literal
# "Item 1.", "Item 1A.", etc. followed by a title.
_ITEM_PATTERNS: dict[str, str] = {
    "item_1":  r"Item\s*1\.\s*Business",
    "item_1a": r"Item\s*1A\.\s*Risk\s*Factors",
    "item_1b": r"Item\s*1B\.\s*Unresolved\s*Staff\s*Comments",
    "item_1c": r"Item\s*1C\.\s*Cybersecurity",
    "item_2":  r"Item\s*2\.\s*Properties",
    "item_3":  r"Item\s*3\.\s*Legal\s*Proceedings",
    "item_7":  r"Item\s*7\.\s*Management",
    "item_7a": r"Item\s*7A\.\s*Quantitative\s*and\s*Qualitative",
    "item_8":  r"Item\s*8\.\s*Financial\s*Statements",
}

# Order matters: we scan for all items, then split the text at each match.
_ITEM_KEYS: list[tuple[str, str]] = list(_ITEM_PATTERNS.items())


@dataclass
class ParsedSection:
    """A single parsed section of a 10-K."""

    section_id: str      # e.g. "item_1a"
    title: str           # e.g. "Item 1A. Risk Factors"
    text: str            # the cleaned text content
    char_count: int      # convenience

    def to_dict(self) -> dict:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "text": self.text,
            "char_count": self.char_count,
        }


def _html_to_text(html: str) -> str:
    """Strip HTML, normalize whitespace, keep paragraph structure."""
    # Use the stdlib html.parser to avoid lxml's MSVC build dependency on Windows.
    soup = BeautifulSoup(html, "html.parser")
    # Drop script/style
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_all_item_matches(text: str) -> list[tuple[int, str, str]]:
    """Return (position, section_id, header) for each Item marker in text."""
    matches: list[tuple[int, str, str]] = []
    for sid, pat in _ITEM_KEYS:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            matches.append((m.start(), sid, m.group(0)))
    matches.sort()
    return matches


def parse_filing(html: str) -> list[ParsedSection]:
    """Parse a 10-K HTML string into a list of named sections.

    Returns sections in document order. Sections that we couldn't locate
    are simply absent from the result — call `parse_filing_with_stats` if
    you need to know the parse rate.

    Two cleanup passes:
    1. Drop sections < 500 chars (internal cross-references, not real Items)
    2. If the same section_id appears multiple times (e.g. once in the TOC,
       once in the real body), keep only the longest one. This is robust
       because the real section is always much longer than the TOC mention.
    """
    text = _html_to_text(html)
    matches = _find_all_item_matches(text)
    if not matches:
        return []
    MIN_SECTION_CHARS = 500
    raw_sections: list[ParsedSection] = []
    for i, (pos, sid, header) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        body = text[pos:end].strip()
        body = body[len(header):].strip()
        if len(body) < MIN_SECTION_CHARS:
            continue
        raw_sections.append(
            ParsedSection(
                section_id=sid,
                title=header,
                text=body,
                char_count=len(body),
            )
        )
    # Dedupe: keep the longest occurrence of each section_id (real > TOC)
    best_by_id: dict[str, ParsedSection] = {}
    for s in raw_sections:
        if s.section_id not in best_by_id or s.char_count > best_by_id[s.section_id].char_count:
            best_by_id[s.section_id] = s
    # Return in canonical item order
    out = [best_by_id[sid] for sid in _ITEM_PATTERNS.keys() if sid in best_by_id]
    return out


def parse_filing_with_stats(html: str) -> tuple[list[ParsedSection], dict]:
    """Like parse_filing, but also returns parse statistics.

    Stats:
    - sections_found: list of section_ids we located
    - sections_missing: list of section_ids that didn't appear
    - parse_rate: fraction of expected sections found
    """
    sections = parse_filing(html)
    found = {s.section_id for s in sections}
    expected = set(_ITEM_PATTERNS.keys())
    missing = sorted(expected - found)
    return sections, {
        "sections_found": sorted(found),
        "sections_missing": missing,
        "parse_rate": len(found) / len(expected),
    }


def parse_filing_file(path: Path) -> list[ParsedSection]:
    """Convenience: read a file and parse it."""
    return parse_filing(Path(path).read_text(encoding="utf-8"))
