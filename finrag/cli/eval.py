"""Eval CLI placeholder. Full implementation in Week 2 (RAGAS).

For now, this exists so the Makefile target `make eval` works, and so we
can iterate on the experiment-runner pattern.
"""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Run an experiment against the eval set.")
console = Console()


@app.command()
def main(
    exp: str = typer.Option("exp_001_naive_baseline", help="Experiment folder name"),
):
    console.print(f"[yellow]Eval runner is a Week-2 deliverable. Skipping {exp}.[/]")
    console.print("Week 1 smoke test is: make query Q=\"...\"")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
