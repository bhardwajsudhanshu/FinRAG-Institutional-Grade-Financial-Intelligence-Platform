"""Update results/leaderboard.json from results/experiments.csv.

The leaderboard is the one-page summary for the README: which experiment
is winning each category, and what the full sorted list looks like.

Usage:
    uv run python tests/eval/update_leaderboard.py [--csv results/experiments.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

LEADERBOARD_SCHEMA_VERSION = "1.0"

# CATEGORY_CONFIG: how to score each category.
# `metric` is the column in experiments.csv. `ascending` says whether lower
# is better (latency, cost) or higher is better (recall, faithfulness).
CATEGORY_CONFIG: dict[str, dict[str, Any]] = {
    "chunking": {"metric": "context_recall", "ascending": False, "primary": True},
    "vectordb": {"metric": "p95_latency_ms", "ascending": True, "primary": False},
    "retrieval": {"metric": "context_recall", "ascending": False, "primary": False},
    "reranker": {"metric": "hit_at_10", "ascending": False, "primary": False},
    "end_to_end": {"metric": "faithfulness", "ascending": False, "primary": True},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("results/experiments.csv"),
        help="Path to the experiments CSV",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/leaderboard.json"),
        help="Path to the leaderboard JSON",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"[FAIL] {args.csv} does not exist", file=sys.stderr)
        return 1

    # Load all rows
    rows: list[dict[str, Any]] = []
    with args.csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numerics; leave None for missing
            for k, v in list(row.items()):
                if v is None or v == "" or v == "None":
                    row[k] = None
                    continue
                try:
                    row[k] = float(v)
                except ValueError:
                    pass
            rows.append(row)

    # Load existing leaderboard (or start fresh)
    leaderboard: dict[str, Any] = {
        "schema_version": LEADERBOARD_SCHEMA_VERSION,
        "last_updated": "",
        "categories": {cat: {"winner": None, "runner_up": None, "metric": cfg["metric"]} for cat, cfg in CATEGORY_CONFIG.items()},
        "experiments": [],
    }
    if args.out.exists():
        try:
            leaderboard = json.loads(args.out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    # Score each category
    for cat, cfg in CATEGORY_CONFIG.items():
        metric = cfg["metric"]
        candidates = [r for r in rows if r.get(metric) is not None]
        candidates.sort(key=lambda r: r[metric], reverse=not cfg["ascending"])
        if not candidates:
            continue
        winner = candidates[0]
        runner = candidates[1] if len(candidates) > 1 else None
        leaderboard["categories"][cat] = {
            "winner": winner["exp_name"],
            "winner_value": winner[metric],
            "runner_up": runner["exp_name"] if runner else None,
            "metric": metric,
        }

    # Build the full sorted list of experiments (by timestamp, newest first)
    sorted_rows = sorted(rows, key=lambda r: r.get("timestamp", ""), reverse=True)
    leaderboard["experiments"] = [
        {
            "exp_name": r["exp_name"],
            "timestamp": r.get("timestamp"),
            "n_questions": r.get("n_questions"),
            "context_recall": r.get("context_recall"),
            "faithfulness": r.get("faithfulness"),
            "answer_relevancy": r.get("answer_relevancy"),
            "hit_at_5": r.get("hit_at_5"),
            "citation_accuracy": r.get("citation_accuracy"),
            "mean_latency_ms": r.get("mean_latency_ms"),
            "total_cost_usd": r.get("total_cost_usd"),
        }
        for r in sorted_rows
    ]
    leaderboard["schema_version"] = LEADERBOARD_SCHEMA_VERSION
    leaderboard["last_updated"] = max(
        (r.get("timestamp") or "" for r in rows), default=""
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(leaderboard, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] wrote leaderboard to {args.out}")
    for cat, info in leaderboard["categories"].items():
        print(f"  {cat:14s} winner: {info.get('winner')!r:35s}  ({info.get('metric')}={info.get('winner_value')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
