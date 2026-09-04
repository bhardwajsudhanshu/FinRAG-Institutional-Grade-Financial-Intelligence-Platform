"""Ask CLI: the smoke test.

Usage:
    uv run python -m finrag.cli.ask "What was Apple's revenue in FY2023?"

This is the end-to-end smoke test for Week 1. It:
1. Loads the sample AAPL 10-K (already ingested)
2. Chunks it (naive 512/50)
3. Builds the in-memory index
4. Retrieves top-K for the question
5. Generates an answer (mock or vertex)
6. Prints the answer, the citations, and the cost
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from finrag.chunking import chunk_sections
from finrag.config import get_settings
from finrag.data.ingest_sec import ingest_sample
from finrag.data.parse_sections import parse_filing
from finrag.generation import get_generator
from finrag.retrieval import build_index, retrieve, results_to_citations

app = typer.Typer(help="Ask a question over ingested SEC filings.")
console = Console()


def _ensure_sample() -> Path:
    """Make sure the sample AAPL filing exists; ingest it if not."""
    settings = get_settings()
    target = settings.data_raw_dir / "AAPL" / "2023-11-03" / "10k.html"
    if not target.exists():
        console.print("[yellow]Sample not found, ingesting...[/]")
        ingest_sample(raw_dir=settings.data_raw_dir)
    return target


def _build_index_from_filing(filing_path: Path) -> tuple:
    """Parse + chunk + embed a single filing. Returns (index, chunks)."""
    settings = get_settings()
    html = filing_path.read_text(encoding="utf-8")
    sections = parse_filing(html)
    if not sections:
        raise RuntimeError(f"No sections parsed from {filing_path}. Check the format.")

    # Pull metadata from the file path
    ticker = filing_path.parent.parent.name
    filing_date = filing_path.parent.name
    chunks = chunk_sections(
        sections=sections,
        ticker=ticker,
        filing_date=filing_date,
        fiscal_year=2023,  # hardcoded for sample
        accession_number="0000320193-23-000106",
    )
    console.print(f"[dim]Parsed {len(sections)} sections, {len(chunks)} chunks from {filing_path.name}[/]")
    index = build_index(chunks)
    return index, chunks


@app.command()
def main(
    question: str = typer.Argument(..., help="The question to ask"),
    top_k: int = typer.Option(5, help="How many chunks to retrieve"),
):
    settings = get_settings()
    console.print(Panel(f"[bold]{question}[/]", title="Question", border_style="cyan"))

    # 1. Make sure the sample filing exists
    sample_path = _ensure_sample()

    # 2. Build the index
    index, chunks = _build_index_from_filing(sample_path)
    console.print(f"[dim]Index built: {len(index)} chunks, dim={get_settings().embedding_dim}[/]")

    # 3. Retrieve
    results = retrieve(index, question, top_k=top_k)
    if not results:
        console.print("[red]No results retrieved.[/]")
        sys.exit(1)
    console.print(f"[dim]Retrieved top {len(results)} chunks (top score={results[0][1]:.3f})[/]")

    # 4. Generate
    generator = get_generator()
    citations = results_to_citations(results)
    contexts = [(chunk.text, citations[i]) for i, (chunk, _score) in enumerate(results)]
    result = generator.generate(question, contexts)

    # 5. Display
    console.print()
    console.print(Panel(Markdown(result.answer), title=f"Answer ({result.model})", border_style="green"))
    console.print()
    console.print(
        f"[dim]Tokens: in={result.input_tokens} out={result.output_tokens}. "
        f"Cost: ${result.cost_usd:.4f}.[/]"
    )
    console.print(f"[dim]Citations: {len(result.citations)} chunks.[/]")


if __name__ == "__main__":
    app()
