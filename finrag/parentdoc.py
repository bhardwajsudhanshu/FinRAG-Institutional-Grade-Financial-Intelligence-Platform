"""Parent-document retrieval (STEP_030, exp_041).

Pattern: index SMALL child chunks for retrieval precision, generate from
their LARGE parents for context coverage. Parents are byte-identical to
exp_001 naive chunks (512/50), so this isolates hierarchy — same parents,
finer retrieval units.

- Parents: `chunk_sections` (naive 512/50) — the familiar chunk_ids.
- Children: naive 256/25 windows *within each parent text*, ids
  `{parent_id}:c{ii:02d}`, metadata carries `parent_id`.
- Query: top-K children by cosine -> unique parents in first-seen order
  (best child score kept) -> top-5 parents as contexts.

Why it should help synthesis/section Q's: the answer often spans a
paragraph boundary that one 512-token parent holds but no single
retrieved chunk isolates; children find the exact sentence, parents
supply the surroundings. Why it might hurt lookup: extra indirection
for facts one chunk already holds.
"""

from __future__ import annotations

from finrag.chunking import Chunk, chunk_sections, naive_chunk_text


def build_parent_child_chunks(
    sections: list,
    ticker: str,
    filing_date: str,
    fiscal_year: int,
    accession_number: str,
    child_size: int = 256,
    child_overlap: int = 25,
    encoding_name: str = "cl100k_base",
) -> tuple[list[Chunk], list[Chunk], dict[str, str]]:
    """Build (parents, children, child_id -> parent_id).

    Parents come from the standard naive chunker verbatim (settings sizes)
    — byte-identical to exp_001, so parent identity stays comparable
    across experiments. Children re-window each parent text; empty
    slivers are dropped.
    """
    if child_size <= 0:
        raise ValueError("child_size must be > 0")
    if child_overlap < 0 or child_overlap >= child_size:
        raise ValueError("child_overlap must be in [0, child_size)")
    parents = chunk_sections(
        sections,
        ticker=ticker,
        filing_date=filing_date,
        fiscal_year=fiscal_year,
        accession_number=accession_number,
    )
    children: list[Chunk] = []
    child_to_parent: dict[str, str] = {}
    for parent in parents:
        if not parent.text.strip():
            continue
        sub = naive_chunk_text(
            parent.text,
            chunk_size=child_size,
            overlap=child_overlap,
            encoding_name=encoding_name,
        )
        for idx, text in enumerate(sub):
            cid = f"{parent.chunk_id}:c{idx:02d}"
            children.append(Chunk(
                chunk_id=cid,
                text=text,
                metadata={**parent.metadata, "chunker": "parent-doc",
                          "parent_id": parent.chunk_id,
                          "child_index": idx},
            ))
            child_to_parent[cid] = parent.chunk_id
    return parents, children, child_to_parent
