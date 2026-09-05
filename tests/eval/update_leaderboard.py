"""Update results/leaderboard.json from results/experiments.csv.

The leaderboard is the one-page summary for the README: which experiment
is winning each category, and what the full sorted list looks like.

**Immutability contract (locked 2026-09-05):**
- The `experiments` list in `results/leaderboard.json` is append-only.
  Once an exp_* row is written, it is never modified, even if a later
  refresh re-derives the leader. The refresh regenerates the `experiments`
  list from `results/experiments.csv` (which is also append-only), so
  in practice no row ever changes — but if `experiments.csv` were ever
  edited in place, the leaderboard would inherit the corruption.
- Every refresh writes an **immutable snapshot** to
  `results/leaderboard_snapshots/leaderboard_<timestamp>.json`. These
  snapshots are write-once. The current `results/leaderboard.json` is
  the latest snapshot, copied for convenience (it is overwritten on
  each refresh, but the snapshots dir is the durable record).
- `results/experiments.csv` is the canonical append-only ledger of
  every experiment ever run. The `exp_001_naive_baseline` row written
  on 2026-09-05T07:45:04 will exist verbatim in this CSV forever.

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
        help="Path to the leaderboard JSON (rolling, overwritten on each refresh)",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path("results/leaderboard_snapshots"),
        help="Directory to write immutable per-refresh snapshots into",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"[FAIL] {args.csv} does not exist", file=sys.stderr)
        return 1

    # Load all rows from the append-only ledger
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

    # Score each category — winner is the experiment with the best value
    # of the category's metric among rows that have a non-null value for
    # that metric. The winner DOES change over time as new experiments
    # arrive, but the *experiments* list below is the full history.
    categories: dict[str, dict[str, Any]] = {}
    for cat, cfg in CATEGORY_CONFIG.items():
        metric = cfg["metric"]
        candidates = [r for r in rows if r.get(metric) is not None]
        candidates.sort(key=lambda r: r[metric], reverse=not cfg["ascending"])
        if not candidates:
            categories[cat] = {
                "winner": None,
                "winner_value": None,
                "runner_up": None,
                "metric": metric,
            }
            continue
        winner = candidates[0]
        runner = candidates[1] if len(candidates) > 1 else None
        categories[cat] = {
            "winner": winner["exp_name"],
            "winner_value": winner[metric],
            "runner_up": runner["exp_name"] if runner else None,
            "metric": metric,
        }

    # Build the full sorted list of experiments (by timestamp, newest first)
    # This is the full append-only history — exp_001 still appears here
    # after exp_002 lands, etc.
    sorted_rows = sorted(rows, key=lambda r: r.get("timestamp", ""), reverse=True)
    experiments_list = [
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

    # Pick the highest timestamp for `last_updated`
    last_updated = max((r.get("timestamp") or "" for r in rows), default="")

    leaderboard: dict[str, Any] = {
        "schema_version": LEADERBOARD_SCHEMA_VERSION,
        "last_updated": last_updated,
        "categories": categories,
        "experiments": experiments_list,
    }

    # Write the rolling leaderboard.json (overwritten each refresh)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(leaderboard, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write an immutable timestamped snapshot. Use a sortable filename so
    # `ls leaderboard_snapshots/` reads chronologically. Filename uses
    # the latest experiment timestamp (or now() if no experiments).
    args.snapshot_dir.mkdir(parents=True, exist_ok=True)
    if last_updated:
        # 2026-09-05T07:45:04 -> 20260905_074504
        snapshot_stamp = last_updated.replace("-", "").replace(":", "").replace("T", "_")[:15]
    else:
        import datetime as _dt
        snapshot_stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = args.snapshot_dir / f"leaderboard_{snapshot_stamp}.json"
    if snapshot_path.exists():
        # If two refreshes happen inside the same second, suffix with a counter
        i = 1
        while True:
            cand = args.snapshot_dir / f"leaderboard_{snapshot_stamp}_{i}.json"
            if not cand.exists():
                snapshot_path = cand
                break
            i += 1
    snapshot_path.write_text(
        json.dumps(leaderboard, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"[OK] wrote rolling leaderboard to {args.out}")
    print(f"[OK] wrote immutable snapshot to {snapshot_path}")
    for cat, info in categories.items():
        print(
            f"  {cat:14s} winner: {info.get('winner')!r:35s}  "
            f"({info.get('metric')}={info.get('winner_value')})"
        )
    print(f"\n  history: {len(experiments_list)} experiments in ledger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
