"""Ingest CLI: `uv run python -m finrag.cli.ingest [--sample]`.

Pulls SEC 10-K filings for the configured ticker set (or one sample filing
for the smoke test) and writes them to data/raw/.
"""

from __future__ import annotations

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from finrag.data.ingest_sec import DEFAULT_TICKERS, ingest, ingest_sample
from finrag.config import get_settings

app = typer.Typer(help="Ingest SEC filings.")
console = Console()


@app.command()
def main(
    sample: bool = typer.Option(False, "--sample", help="Ingest 1 sample filing for the smoke test."),
    tickers: str = typer.Option("", help="Comma-separated tickers (default: all 20)"),
    form: str = typer.Option("10-K", help="Form type: 10-K (annual) or 10-Q (quarterly)"),
    years: int = typer.Option(3, help="How many years back to pull"),
):
    settings = get_settings()
    if sample:
        console.print("[bold cyan]Ingesting sample filing (AAPL FY2023 10-K)...[/]")
        df = ingest_sample(raw_dir=settings.data_raw_dir)
    else:
        t_list = [t.strip() for t in tickers.split(",") if t.strip()] or DEFAULT_TICKERS
        console.print(f"[bold cyan]Ingesting {len(t_list)} tickers × {years}y ({form})...[/]")
        df = ingest(tickers=t_list, raw_dir=settings.data_raw_dir, form_type=form, years=years)

    table = Table(title=f"Ingested {len(df)} filings")
    table.add_column("Ticker", style="cyan")
    table.add_column("FY", style="magenta")
    table.add_column("Filed", style="green")
    table.add_column("Local path", style="dim")
    for _, row in df.head(10).iterrows():
        table.add_row(
            str(row.get("ticker", "")),
            str(row.get("fiscal_year", "")),
            str(row.get("filing_date", "")),
            str(row.get("local_path", "")),
        )
    if len(df) > 10:
        console.print(table)
        console.print(f"  ... and {len(df) - 10} more")
    else:
        console.print(table)


if __name__ == "__main__":
    app()
