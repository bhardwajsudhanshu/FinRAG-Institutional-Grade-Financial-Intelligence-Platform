"""Eval CLI: run an experiment against the Q&A set.

Usage:
    # Full eval (requires a built qa_pairs.jsonl)
    uv run python -m finrag.cli.eval --exp exp_001_naive_baseline

    # Smoke test on 5 Q's
    uv run python -m finrag.cli.eval --exp exp_001_naive_baseline --limit 5

This:
1. Loads the Q&A set (data/eval/qa_pairs.jsonl by default)
2. Builds the chunk+embedding index for the eval filings
3. Runs the RAG pipeline for each Q (retrieve -> generate)
4. Scores with RAGAS (context_recall, faithfulness, answer_relevancy)
   plus our custom metrics (hit@5, citation_accuracy, mean_latency)
5. Appends one row to results/experiments.csv
6. Writes per-Q details to results/<exp_name>/per_question.jsonl
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from finrag.config import get_settings
from finrag.eval import run_experiment

app = typer.Typer(help="Run an experiment against the Q&A set.")
console = Console()

# Locked CSV schema. New metrics go at the end so we don't break
# downstream pandas readers.
EXPERIMENTS_CSV_FIELDS = [
    "exp_name",
    "timestamp",
    "n_questions",
    "n_filings",
    "n_chunks",
    "context_recall",
    "faithfulness",
    "answer_relevancy",
    "hit_at_5",
    "citation_accuracy",
    "mean_latency_ms",
    "total_cost_usd",
]


def _limit_qa_file(src: Path, dst: Path, n: int) -> int:
    """Copy the first N lines of a JSONL file. Returns lines written."""
    written = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for i, line in enumerate(fin):
            if i >= n:
                break
            fout.write(line)
            written += 1
    return written


def _append_to_csv(csv_path: Path, row: dict) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXPERIMENTS_CSV_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


@app.command()
def main(
    exp: str = typer.Option("exp_001_naive_baseline", help="Experiment name (folder)"),
    qa_path: Path = typer.Option(
        Path("data/eval/qa_pairs.jsonl"), help="Q&A JSONL file"
    ),
    out_csv: Path = typer.Option(
        Path("results/experiments.csv"), help="CSV to append results to"
    ),
    per_q_out: Path = typer.Option(
        None, help="Optional path to write per-Q details (defaults to results/<exp>/per_question.jsonl)"
    ),
    top_k: int = typer.Option(5, help="Number of chunks to retrieve per Q"),
    limit: int = typer.Option(0, help="Limit to N Q's (0 = no limit, smoke test otherwise)"),
):
    settings = get_settings()
    if not qa_path.exists():
        console.print(f"[red]Q&A set not found at {qa_path}[/]")
        console.print("Generate one first: [cyan]uv run python tests/eval/generate_qa_pairs.py[/]")
        raise typer.Exit(code=1)

    # Smoke test: write a limited copy so run_experiment loads only N Q's
    work_qa = qa_path
    if limit and limit > 0:
        work_qa = qa_path.with_name(qa_path.stem + f".limit{limit}.jsonl")
        n_written = _limit_qa_file(qa_path, work_qa, limit)
        console.print(f"[dim]Smoke test: {n_written} Q's -> {work_qa}[/]")

    console.print(f"[bold]Running experiment:[/] {exp}")
    console.print(f"  Q&A set:    {work_qa}")
    console.print(f"  Backend:    embedder={settings.embedder_backend} generator={settings.generator_backend}")
    console.print(f"  top_k:      {top_k}")

    # Default per-Q output path: results/<exp>/per_question.jsonl
    per_q_target = per_q_out if per_q_out is not None else Path("results") / exp / "per_question.jsonl"
    per_q_target.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = run_experiment(
            exp_name=exp,
            qa_path=work_qa,
            top_k=top_k,
            per_q_out=per_q_target,
        )
    except Exception as e:
        logger.exception("Experiment failed")
        console.print(f"[red]Experiment failed: {e}[/]")
        raise typer.Exit(code=1)

    # Persist
    _append_to_csv(out_csv, result.to_csv_row())
    # If the runner didn't write incrementally (e.g. it failed mid-run
    # and a partial file already exists), rewrite the canonical version
    # from the in-memory list so the file is always complete.
    if not per_q_target.exists() or per_q_target.stat().st_size == 0:
        with per_q_target.open("w", encoding="utf-8") as f:
            for row in result.per_question:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Pretty print
    table = Table(title=f"Experiment: {exp}", show_lines=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    for k in EXPERIMENTS_CSV_FIELDS:
        if k in ("exp_name", "timestamp"):
            continue
        v = getattr(result, k)
        if isinstance(v, float):
            v = f"{v:.4f}"
        elif v is None:
            v = "(skipped)"
        table.add_row(k, str(v))
    console.print(table)
    console.print(f"\n[dim]Appended row to {out_csv}[/]")
    console.print(f"[dim]Per-Q details:  {per_q_target}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(app() or 0)
