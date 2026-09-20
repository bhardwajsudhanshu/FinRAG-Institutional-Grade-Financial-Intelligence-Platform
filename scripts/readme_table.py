"""Regenerate README's results table + counts from the ledger (STEP_042).

Reads `results/experiments.csv` (locked schema) and rewrites the section
between `<!-- RESULTS:START -->` / `<!-- RESULTS:END -->` in README.md,
plus the `N benchmarked experiments` / `M tests` tagline counts.

Usage:
    uv run python scripts/readme_table.py            # rewrite in place
    uv run python scripts/readme_table.py --check    # exit 1 if stale (CI hook)

Design notes:
- The CSV carries metrics but NOT human labels: `EXP_META` maps
  exp_name -> (table label, retrieval label). New experiments add two
  lines here (loud KeyError otherwise — silent mislabeling is worse).
- `hit@5_content` renders em-dash for frozen pre-fix rows (None).
- Test count is AST-derived (`def test_*` in tests/**/test_*.py) —
  deterministic, offline, no pytest run needed.
- Bold applies ONLY to current column maxima (recomputed each run, so a
  dethroned leader loses its bold automatically).
"""

from __future__ import annotations

import argparse
import ast
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_START = "<!-- RESULTS:START -->"
RESULTS_END = "<!-- RESULTS:END -->"

# exp_name -> (table label, retrieval label). Two lines per new experiment.
EXP_META: dict[str, tuple[str, str]] = {
    "exp_001_naive_baseline": ("exp_001 naive baseline", "dense"),
    "exp_002_recursive": ("exp_002 recursive chunking", "dense"),
    "exp_003_semantic": ("exp_003 semantic chunking", "dense"),
    "exp_004_structural": ("exp_004 structural chunking", "dense"),
    "exp_020_bm25": ("exp_020 BM25", "bm25"),
    "exp_021_hybrid_rrf": ("exp_021 hybrid RRF", "hybrid"),
    "exp_022_hybrid_qdrant": ("exp_022 hybrid + live Qdrant", "hybrid"),
    "exp_030_flash_rerank": ("exp_030 + Flash re-rank", "hybrid+rerank"),
    "exp_031_minilm_rerank": ("exp_031 MiniLM re-rank", "hybrid+rerank"),
    "exp_041_parent_doc": ("exp_041 parent-doc", "child→parent"),
    "exp_042_hybrid_parent": ("exp_042 hybrid-parent", "child-fused"),
    "exp_043_multi_query": ("exp_043 multi-query", "dense+expansion"),
    "exp_044_hyde": ("exp_044 HyDE", "dense+hypothetical"),
    "exp_045_hybrid_multiquery": ("exp_045 hybrid+multiquery", "hybrid+expansion"),
    "exp_046_hybrid_hyde": ("exp_046 hybrid+HyDE", "hybrid+hypothetical"),
}

COLUMNS = ["context_recall", "faithfulness", "hit_at_5_content", "citation_accuracy"]
HEADERS = ["Experiment", "Retrieval", "context_recall", "faithfulness",
           "hit@5_content", "citation_acc"]


def _num(value: str | None) -> float | None:
    if value is None or value == "" or value == "None":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_ledger(csv_path: Path) -> list[dict]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        name = row.get("exp_name", "")
        if name not in EXP_META:
            raise KeyError(
                f"Experiment {name!r} missing from EXP_META in "
                f"{Path(__file__).name} — add its (label, retrieval) line.")
    return rows


def render_table(rows: list[dict]) -> str:
    maxima: dict[str, float] = {}
    for col in COLUMNS:
        vals = [_num(r.get(col)) for r in rows]
        vals = [v for v in vals if v is not None]
        if vals:
            maxima[col] = max(vals)

    def is_max(row: dict, col: str) -> bool:
        v = _num(row.get(col))
        return v is not None and col in maxima and v == maxima[col]

    def cell(row: dict, col: str) -> str:
        v = _num(row.get(col))
        if v is None:
            return "—"
        text = f"{v:.4f}"
        # Bold unique maxima only (ties stay plain — no false winners).
        if is_max(row, col) and sum(1 for r in rows if is_max(r, col)) == 1:
            return f"**{text}**"
        return text

    lines = ["| " + " | ".join(HEADERS) + " |",
             "|" + "|".join(["---"] * len(HEADERS)) + "|"]
    for row in rows:
        label, retrieval = EXP_META[row["exp_name"]]
        # Bold the label iff the row uniquely leads EVERY metric column
        # (the sweep leader — transfers automatically on dethrone).
        if all(is_max(row, c) and sum(1 for r in rows if is_max(r, c)) == 1
               for c in COLUMNS):
            label = f"**{label}**"
        lines.append("| " + " | ".join([label, retrieval] +
                                       [cell(row, c) for c in COLUMNS]) + " |")
    return "\n".join(lines) + "\n"


def count_tests(tests_dir: Path) -> int:
    """Count pytest CASES (not functions): `def test_*` plus
    `@pytest.mark.parametrize` multipliers — matches `pytest -q` totals.

    Only literal argvalues lists are counted; dynamic marks count 1
    (documented undercount, never overcount).
    """
    count = 0
    for path in sorted(tests_dir.rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            cases = 1
            for dec in node.decorator_list:
                func = dec.func if isinstance(dec, ast.Call) else None
                name = ""
                if isinstance(func, ast.Attribute):
                    name = func.attr
                if name == "parametrize" and len(dec.args) >= 2:
                    vals = dec.args[1]
                    if isinstance(vals, (ast.List, ast.Tuple)):
                        cases *= max(1, len(vals.elts))
            count += cases
    return count


def render_counts(n_exps: int, n_tests: int) -> str:
    return f"{n_exps} benchmarked experiments, {n_tests} tests"


def update_readme(readme_path: Path, table_md: str, counts_md: str) -> tuple[str, bool]:
    """Rewrite the marked table section + tagline counts. Returns (new_text, changed)."""
    text = readme_path.read_text(encoding="utf-8")
    if RESULTS_START not in text or RESULTS_END not in text:
        raise ValueError(f"Markers {RESULTS_START}/{RESULTS_END} missing in {readme_path}")
    pattern = re.compile(re.escape(RESULTS_START) + r".*?" + re.escape(RESULTS_END),
                         re.DOTALL)
    new_text = pattern.sub(f"{RESULTS_START}\n{table_md}{RESULTS_END}", text, count=1)
    counts_pattern = re.compile(r"\d+ benchmarked experiments, \d+ tests")
    new_text2, _ = counts_pattern.subn(counts_md, new_text, count=1)
    return new_text2, new_text2 != text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 (no write) when README differs from generated")
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    parser.add_argument("--ledger", type=Path, default=ROOT / "results" / "experiments.csv")
    parser.add_argument("--tests", type=Path, default=ROOT / "tests")
    args = parser.parse_args()

    rows = load_ledger(args.ledger)
    table_md = render_table(rows)
    counts_md = render_counts(len(rows), count_tests(args.tests))
    new_text, changed = update_readme(args.readme, table_md, counts_md)
    if args.check:
        print("STALE" if changed else "FRESH")
        return 1 if changed else 0
    if changed:
        args.readme.write_text(new_text, encoding="utf-8")
        print(f"[OK] README refreshed: {len(rows)} rows")
    else:
        print("[OK] README already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
