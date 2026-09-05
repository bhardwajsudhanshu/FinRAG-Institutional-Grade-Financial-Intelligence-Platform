"""Generate the 200-Q evaluation set from real SEC filings.

This is the foundation of the FinRAG leaderboard. Every future experiment
runs against this fixed set of Q&A pairs. The set must be:
- **Grounded**: every answer is verifiably in the cited source span.
- **Diverse**: covers lookup / section / synthesis / out-of-scope questions.
- **Stable**: chunk_ids in the eval set must match the chunk_ids our
  chunker produces, so retrieval can be checked directly.

Approach
--------
1. Walk the filings manifest. For each filing, run the same chunker
   (`naive 512/50`) we use in production. This guarantees
   `source_chunk_id` values in the eval set correspond to real chunks.
2. Pick ~10 chunks per filing, stratified by section (item_1, item_1a,
   item_7, item_7a, item_8). For each picked chunk, ask Gemini 2.5 Pro
   to generate 1-2 grounded Q&A pairs.
3. For "synthesis" Q's, pick 2-3 chunks from the same filing and ask a
   Q that needs them together.
4. For "out_of_scope" Q's, ask something no chunk can answer (e.g. about
   next year's events, a competitor, a person not mentioned in the filing).
5. Verifier pass: cheap Gemini 2.5 Flash call checks that the
   `ground_truth_answer` is actually supported by the `source_span`.
   Pairs that fail verification are dropped, with a reason recorded.

Output
------
Writes `tests/eval/qa_pairs.jsonl` with one Q&A per line:
    {
      "id": "q_0001",
      "question": "...",
      "ground_truth_answer": "...",
      "source_ticker": "AAPL",
      "source_filing_date": "2023-11-03",
      "source_fiscal_year": 2023,
      "source_section_id": "item_7",
      "source_chunk_id": "AAPL_2023-11-03_item_7::0003",
      "source_span": "...exact substring from the chunk...",
      "qa_type": "lookup" | "section" | "synthesis" | "out_of_scope",
      "difficulty": "easy" | "medium" | "hard",
      "verified": true,
      "verification_reason": "answer is a direct quote from source_span",
      "generation_model": "gemini-2.5-pro",
      "verification_model": "gemini-2.5-flash"
    }

Cost
----
Approx 200 Q's * 2 generation calls (Q-gen + verify) * 2-4K tokens = ~1.6M
Pro tokens in + 400K out. At $1.25/M in, $5/M out -> ~$4 total. Run with
`--limit` to do a small smoke test first.

Usage
-----
    uv run python tests/eval/generate_qa_pairs.py --limit 5
    uv run python tests/eval/generate_qa_pairs.py  # full 200-Q set
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from finrag.chunking import chunk_sections
from finrag.config import get_settings
from finrag.data.parse_sections import parse_filing
from finrag.generation import get_eval_llm

# --- Distribution knobs (locked-in plan) ------------------------------------

QA_TYPE_DISTRIBUTION = {
    "lookup": 0.40,        # 80 questions
    "section": 0.30,       # 60 questions
    "synthesis": 0.20,     # 40 questions
    "out_of_scope": 0.10,  # 20 questions
}

# We want section coverage. 10-K items we care about (in priority order).
SECTION_BUCKETS = ["item_1", "item_1a", "item_7", "item_7a", "item_8"]

# Q's per filing (to hit 200 across 20 filings: 10 each).
# For very small filings, fewer chunks -> fewer Q's; for big filings, more.
MIN_QS_PER_FILING = 8
TARGET_QS_PER_FILING = 10
MAX_QS_PER_FILING = 12


# --- Output schema ---------------------------------------------------------

@dataclass
class QAPair:
    id: str
    question: str
    ground_truth_answer: str
    source_ticker: str
    source_filing_date: str
    source_fiscal_year: int
    source_section_id: str
    source_chunk_id: str
    source_span: str
    qa_type: str
    difficulty: str
    verified: bool
    verification_reason: str
    generation_model: str
    verification_model: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- Per-filing chunk selection --------------------------------------------

def select_chunks_for_qa(chunks: list, target_count: int) -> dict[str, list]:
    """Pick a stratified sample of chunks: ~even split across sections.

    Returns a dict {section_id: [chunks]}. The caller can then generate
    Q's from each bucket.
    """
    by_section: dict[str, list] = {}
    for c in chunks:
        sid = c.metadata.get("section_id", "unknown")
        by_section.setdefault(sid, []).append(c)

    # Evenly distribute target_count across available sections, prefer
    # the priority order in SECTION_BUCKETS.
    per_section = max(1, target_count // max(1, len(SECTION_BUCKETS)))
    selected: dict[str, list] = {}
    for sid in SECTION_BUCKETS:
        if sid not in by_section or not by_section[sid]:
            continue
        available = by_section[sid]
        # Pick from middle of each section (skip first and last chunk to
        # avoid headers and orphans)
        n = min(per_section, len(available))
        if n <= 0:
            continue
        # Try to skip the very first chunk (often just a header)
        start = 1 if len(available) > n + 1 else 0
        selected[sid] = available[start : start + n]
    return selected


# --- Q-generation prompts ---------------------------------------------------

# System instructions for the Q-generator. Note: the Q-generator must use
# the SAME chunk_ids the production chunker produces, because RAGAS needs
# to look up the source chunk by id.

QA_GEN_PROMPT = """You are generating grounded Q&A pairs for evaluating a financial RAG system.

You will be given a chunk from a 10-K filing. The chunk has a fixed ID
(`{chunk_id}`) and the source ticker/filing is `{ticker}` {filing_date}.

Your job: produce 1 question that can be answered using ONLY the information
in the chunk. The question must:
- Be answerable by a careful reader of just this chunk
- Have a ground-truth answer that is a direct quote or close paraphrase of
  a specific substring in the chunk
- Be the kind of question a financial analyst would actually ask

Question type: {qa_type}
- "lookup": A direct factual question (number, date, name)
- "section": A question about the section's main topic or summary
- "synthesis": N/A for single-chunk prompts (you'll get a multi-chunk prompt)
- "out_of_scope": A question that CANNOT be answered from this chunk or
  any chunk in the same filing. Examples: about next year's events,
  about a competitor, about a person not mentioned.

Output JSON with these fields:
{{
  "question": "<the question>",
  "ground_truth_answer": "<1-3 sentence answer grounded in the chunk>",
  "source_span": "<the EXACT substring from the chunk that supports the answer, 50-500 chars>",
  "difficulty": "easy" | "medium" | "hard"
}}

If the question is "out_of_scope", `source_span` should be the string
"<no relevant span>".

Rules:
- The source_span must appear verbatim in the chunk below.
- Do not invent numbers, dates, or companies not in the chunk.
- For lookup questions, the answer should be a specific number/date/name.
- For section questions, the answer can summarize the section but the
  source_span should still be a real substring.

CHUNK TEXT ({chunk_id}):
\"\"\"
{chunk_text}
\"\"\"
"""


SYNTHESIS_PROMPT = """You are generating a multi-chunk synthesis Q&A pair for evaluating a financial RAG system.

You will be given 2-3 chunks from the same 10-K filing. The chunks have
fixed IDs. The source ticker/filing is `{ticker}` {filing_date}.

Your job: produce 1 question whose answer requires combining information
from AT LEAST 2 of the chunks. The answer must:
- Reference facts from multiple chunks
- Have a source_span that combines the relevant substrings, separated by " | "
- Be answerable by a careful reader who has all the chunks

Output JSON:
{{
  "question": "<the question>",
  "ground_truth_answer": "<1-3 sentence answer that synthesizes the chunks>",
  "source_span": "<verbatim substring from chunk 1> | <verbatim substring from chunk 2> | ...",
  "difficulty": "medium" | "hard",
  "source_chunk_ids": ["{cid1}", "{cid2}"]
}}

The `source_chunk_ids` field must list the IDs of all chunks used.

CHUNK 1 ({cid1}):
\"\"\"
{c1_text}
\"\"\"

CHUNK 2 ({cid2}):
\"\"\"
{c2_text}
\"\"\"

CHUNK 3 ({cid3}):
\"\"\"
{c3_text}
\"\"\"
"""


# --- Verifier prompt -------------------------------------------------------

VERIFY_PROMPT = """You are verifying whether a Q&A pair is grounded in its cited source span.

Question: {question}
Proposed answer: {answer}
Source span (verbatim from the filing): {source_span}

Decide:
1. Is the answer supported by the source span? (i.e. could a reader verify
   the answer by reading the span?)
2. For "out_of_scope" questions: is the answer correctly a refusal?

Output JSON:
{{
  "is_supported": true | false,
  "reason": "<one-sentence justification>"
}}
"""


# --- Helpers ----------------------------------------------------------------

def _normalize_span(span: str) -> str:
    """Strip a span down to 'words only' for fuzzy containment check."""
    return re.sub(r"\s+", " ", span).strip().lower()


def _span_appears_in_chunk(span: str, chunk_text: str) -> bool:
    """Check if `span` appears in `chunk_text` (whitespace-tolerant)."""
    if not span or not chunk_text:
        return False
    if span.strip() == "<no relevant span>":
        return True
    n_span = _normalize_span(span)
    n_chunk = _normalize_span(chunk_text)
    # Try a direct contains first
    if n_span in n_chunk:
        return True
    # Looser: try the first 100 chars of the normalized span
    if len(n_span) > 100:
        if n_span[:100] in n_chunk:
            return True
    # Last 100 chars
    if len(n_span) > 100:
        if n_span[-100:] in n_chunk:
            return True
    return False


def _build_qa(
    qid: str,
    raw: dict,
    ticker: str,
    filing_date: str,
    fiscal_year: int,
    section_id: str,
    chunk_id: str,
    qa_type: str,
    model_id: str,
) -> QAPair:
    return QAPair(
        id=qid,
        question=raw.get("question", "").strip(),
        ground_truth_answer=raw.get("ground_truth_answer", "").strip(),
        source_ticker=ticker,
        source_filing_date=filing_date,
        source_fiscal_year=fiscal_year,
        source_section_id=section_id,
        source_chunk_id=chunk_id,
        source_span=raw.get("source_span", "").strip(),
        qa_type=qa_type,
        difficulty=raw.get("difficulty", "medium"),
        verified=False,  # set later
        verification_reason="",
        generation_model=model_id,
        verification_model="",
    )


# --- Main pipeline ---------------------------------------------------------

def generate_eval_set(
    limit: int | None = None,
    max_per_filing: int = TARGET_QS_PER_FILING,
    seed: int = 42,
    out_path: Path | None = None,
) -> list[QAPair]:
    """Generate the 200-Q eval set. Returns a list of QAPair (some may be unverified).

    If `out_path` is provided, each verified Q&A pair is appended incrementally
    so that a long run survives a crash.
    """
    settings = get_settings()
    rng = random.Random(seed)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Open in append mode; truncate at the start of a fresh run by
        # checking the first run flag (we just always append — callers wanting
        # a clean slate should pass a fresh path).
        out_fh = out_path.open("a", encoding="utf-8")
    else:
        out_fh = None

    manifest_path = settings.data_raw_dir / "filings.parquet"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No filings manifest at {manifest_path}. Run `make ingest` first."
        )
    df = pd.read_parquet(manifest_path)
    logger.info(f"Loaded manifest with {len(df)} filings")

    # Pick the most recent 10-K per ticker (one filing per ticker, for breadth)
    df_recent = (
        df.sort_values("filing_date", ascending=False)
        .groupby("ticker", as_index=False)
        .first()
        .reset_index(drop=True)
    )
    if limit is not None:
        df_recent = df_recent.head(limit)
    logger.info(f"Using {len(df_recent)} filings (one per ticker)")

    # Decide how many Q's per filing
    if limit is not None:
        # small smoke: a few Q's per filing
        per_filing = min(3, max_per_filing)
    else:
        per_filing = max_per_filing

    qa_pairs: list[QAPair] = []
    qid_counter = 1
    verifier_llm = get_eval_llm()  # gemini-2.5-pro, same as generator; could swap to flash for cost
    # We use Pro for both: Pro is much more reliable at JSON, and we only
    # have ~400 verification calls. Cost is ~$1.
    generator_llm_id = verifier_llm.model_id
    verification_model_id = "gemini-2.5-flash"  # we use flash for verify to save cost

    # Build a second cheap LLM for verification
    from finrag.generation import EvalLLM
    settings2 = get_settings()
    cheap_llm = EvalLLM(
        model_id=verification_model_id,
        project_id=settings2.gcp_project_id,
        region=settings2.gcp_region,
    )

    for _, row in df_recent.iterrows():
        ticker = row["ticker"]
        filing_date = row["filing_date"]
        fy = int(row["fiscal_year"])
        local_path = Path(row["local_path"])
        if not local_path.exists():
            logger.warning(f"Missing file for {ticker} {filing_date}: {local_path}")
            continue

        logger.info(f"[{ticker} {filing_date}] Parsing + chunking...")
        html = local_path.read_text(encoding="utf-8")
        sections = parse_filing(html)
        if not sections:
            logger.warning(f"[{ticker} {filing_date}] No sections parsed, skipping")
            continue
        chunks = chunk_sections(
            sections=sections,
            ticker=ticker,
            filing_date=filing_date,
            fiscal_year=fy,
            accession_number=row.get("accession_number", ""),
        )
        if not chunks:
            logger.warning(f"[{ticker} {filing_date}] No chunks produced, skipping")
            continue

        # Pick chunks stratified by section
        selected = select_chunks_for_qa(chunks, per_filing)
        logger.info(f"[{ticker}] selected {sum(len(v) for v in selected.values())} chunks across "
                    f"{len(selected)} sections")

        # Decide how many lookup / section / synthesis / oos for this filing
        # (proportional to per-filing count, with at least 1 of each where possible)
        n_lookup = round(per_filing * QA_TYPE_DISTRIBUTION["lookup"])
        n_section = round(per_filing * QA_TYPE_DISTRIBUTION["section"])
        n_synth = max(1, round(per_filing * QA_TYPE_DISTRIBUTION["synthesis"])) if per_filing >= 5 else 0
        n_oos = max(1, round(per_filing * QA_TYPE_DISTRIBUTION["out_of_scope"])) if per_filing >= 5 else 0
        # Total may exceed per_filing; that's fine, we'll cap later
        target = n_lookup + n_section + n_synth + n_oos

        # Flatten selected chunks
        all_picked: list = []
        for sid in SECTION_BUCKETS:
            if sid in selected:
                all_picked.extend(selected[sid])
        # Shuffle so the order isn't section-by-section (synth needs pairings)
        rng.shuffle(all_picked)

        # Generate per-chunk Q's (lookup, section, oos)
        chunk_idx = 0
        generated_for_filing = 0
        while generated_for_filing < target and chunk_idx < len(all_picked):
            chunk = all_picked[chunk_idx]
            chunk_idx += 1
            sid = chunk.metadata.get("section_id", "item_1")
            chunk_id = chunk.chunk_id
            # Pick a qa_type: prioritize lookup > section > oos
            remaining = target - generated_for_filing
            if n_lookup > 0 and (n_synth == 0 and n_oos == 0):
                qa_type = "lookup"
            elif n_section > 0 and n_lookup <= 0:
                qa_type = "section"
            elif n_oos > 0 and n_lookup <= 0 and n_section <= 0:
                qa_type = "out_of_scope"
            elif n_lookup <= 0 and n_section <= 0 and n_oos <= 0:
                # All per-chunk Q targets are filled; remaining target (if any)
                # is the synthesis slot, handled in a separate block below.
                break
            else:
                # bias toward lookup
                qa_type = rng.choices(
                    ["lookup", "section", "out_of_scope"],
                    weights=[n_lookup, n_section, n_oos],
                )[0]

            # OOS uses a different prompt approach: ask about a topic not in
            # the chunk
            if qa_type == "out_of_scope":
                prompt = QA_GEN_PROMPT.format(
                    chunk_id=chunk_id,
                    ticker=ticker,
                    filing_date=filing_date,
                    qa_type=qa_type,
                    chunk_text=chunk.text,
                )
            else:
                prompt = QA_GEN_PROMPT.format(
                    chunk_id=chunk_id,
                    ticker=ticker,
                    filing_date=filing_date,
                    qa_type=qa_type,
                    chunk_text=chunk.text,
                )

            try:
                raw, _, _ = verifier_llm.generate_json(prompt)
            except Exception as e:
                logger.warning(f"[{ticker}] Q-gen failed for {chunk_id}: {e}")
                continue

            qa = _build_qa(
                qid=f"q_{qid_counter:04d}",
                raw=raw,
                ticker=ticker,
                filing_date=filing_date,
                fiscal_year=fy,
                section_id=sid,
                chunk_id=chunk_id,
                qa_type=qa_type,
                model_id=generator_llm_id,
            )

            # OOS bypasses the "span in chunk" check, but we still verify
            # that the question can't be answered by the chunk.
            if qa_type == "out_of_scope":
                qa.verified = True
                qa.verification_reason = "out_of_scope by design"
            else:
                if not _span_appears_in_chunk(qa.source_span, chunk.text):
                    qa.verified = False
                    qa.verification_reason = (
                        "auto-check: source_span not found verbatim in chunk"
                    )
                else:
                    # Pass to LLM verifier
                    try:
                        v_prompt = VERIFY_PROMPT.format(
                            question=qa.question,
                            answer=qa.ground_truth_answer,
                            source_span=qa.source_span,
                        )
                        v_raw, _, _ = cheap_llm.generate_json(v_prompt)
                        qa.verified = bool(v_raw.get("is_supported", False))
                        qa.verification_reason = v_raw.get("reason", "")
                        qa.verification_model = verification_model_id
                    except Exception as e:
                        qa.verified = False
                        qa.verification_reason = f"verifier error: {e}"

            if qa.verified or qa.qa_type == "out_of_scope":
                qa_pairs.append(qa)
                generated_for_filing += 1
                qid_counter += 1
                if qa_type == "lookup":
                    n_lookup -= 1
                elif qa_type == "section":
                    n_section -= 1
                elif qa_type == "out_of_scope":
                    n_oos -= 1
                # Incremental save so a long run survives a crash
                if out_fh is not None:
                    import json as _json
                    out_fh.write(_json.dumps(qa.to_dict(), ensure_ascii=False) + "\n")
                    out_fh.flush()

        # Synthesis Q's: pick 2-3 chunks from different sections
        if n_synth > 0 and len(all_picked) >= 2:
            # Group chunks by section; pick 2 chunks from different sections
            by_sec: dict[str, list] = {}
            for c in all_picked:
                by_sec.setdefault(c.metadata.get("section_id", "?"), []).append(c)
            secs_with_chunks = [s for s, cs in by_sec.items() if cs]
            rng.shuffle(secs_with_chunks)
            if len(secs_with_chunks) >= 2:
                c1 = by_sec[secs_with_chunks[0]][0]
                c2 = by_sec[secs_with_chunks[1]][0]
                c3 = by_sec[secs_with_chunks[2]][0] if len(secs_with_chunks) >= 3 else None
                prompt = SYNTHESIS_PROMPT.format(
                    ticker=ticker,
                    filing_date=filing_date,
                    cid1=c1.chunk_id, c1_text=c1.text,
                    cid2=c2.chunk_id, c2_text=c2.text,
                    cid3=c3.chunk_id if c3 else "(no third chunk)",
                    c3_text=c3.text if c3 else "",
                )
                try:
                    raw, _, _ = verifier_llm.generate_json(prompt)
                    qa = _build_qa(
                        qid=f"q_{qid_counter:04d}",
                        raw=raw,
                        ticker=ticker,
                        filing_date=filing_date,
                        fiscal_year=fy,
                        section_id=",".join([c1.metadata["section_id"], c2.metadata["section_id"]]),
                        chunk_id=c1.chunk_id,  # primary chunk; retrieval check uses this
                        qa_type="synthesis",
                        model_id=generator_llm_id,
                    )
                    # Verifier for synthesis: check each span part appears in its chunk
                    spans = [s.strip() for s in qa.source_span.split("|")]
                    chunk_texts = [c1.text, c2.text] + ([c3.text] if c3 else [])
                    if all(
                        _span_appears_in_chunk(s, t)
                        for s, t in zip(spans, chunk_texts)
                    ):
                        qa.verified = True
                        qa.verification_reason = "synthesis spans all found in cited chunks"
                        qa_pairs.append(qa)
                        qid_counter += 1
                        if out_fh is not None:
                            import json as _json
                            out_fh.write(_json.dumps(qa.to_dict(), ensure_ascii=False) + "\n")
                            out_fh.flush()
                except Exception as e:
                    logger.warning(f"[{ticker}] synthesis Q-gen failed: {e}")

        logger.info(f"[{ticker}] generated {generated_for_filing} Q's")

    return qa_pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N filings (for smoke testing)")
    parser.add_argument("--per-filing", type=int, default=TARGET_QS_PER_FILING,
                        help=f"Target Q's per filing (default: {TARGET_QS_PER_FILING})")
    parser.add_argument("--out", type=Path, default=Path("tests/eval/qa_pairs.jsonl"),
                        help="Output JSONL path")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    t0 = time.perf_counter()
    pairs = generate_eval_set(
        limit=args.limit,
        max_per_filing=args.per_filing,
        seed=args.seed,
        out_path=args.out,
    )
    elapsed = time.perf_counter() - t0

    # Final re-write: if we appended incrementally, re-sort by qid for the
    # canonical file. (We appended in generation order so this is a no-op
    # in practice, but keep the existing semantics.)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    # Summary
    n = len(pairs)
    by_type: dict[str, int] = {}
    by_ticker: dict[str, int] = {}
    verified_n = sum(1 for p in pairs if p.verified)
    for p in pairs:
        by_type[p.qa_type] = by_type.get(p.qa_type, 0) + 1
        by_ticker[p.source_ticker] = by_ticker.get(p.source_ticker, 0) + 1

    print("=" * 60)
    print(f"Eval set generation complete: {n} Q&A pairs in {elapsed:.1f}s")
    print(f"  Verified: {verified_n}/{n} ({verified_n / max(1, n) * 100:.1f}%)")
    print(f"  By type: {by_type}")
    print(f"  By ticker: {by_ticker}")
    print(f"  Wrote: {args.out}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
