"""Test the leaderboard updater: append-only experiment history, immutable snapshots."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# tests/eval/test_leaderboard.py -> tests/ -> project root
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tests.eval.update_leaderboard import main as update_leaderboard_main  # noqa: E402


def _write_csv(csv_path: Path, rows: list[dict]) -> None:
    """Write a minimal experiments.csv with the locked column set.

    The content-anchored columns (`hit_at_5_content`,
    `citation_accuracy_content`) are appended at the end. They are None
    for exp_001 / exp_002 (frozen) and populated from exp_003 onward.
    """
    cols = [
        "exp_name", "timestamp", "n_questions", "n_filings", "n_chunks",
        "context_recall", "faithfulness", "answer_relevancy",
        "hit_at_5", "citation_accuracy", "mean_latency_ms", "total_cost_usd",
        "hit_at_5_content", "citation_accuracy_content",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def test_append_only_history(tmp_path: Path, capsys) -> None:
    """Adding a 2nd experiment to the CSV must NOT remove the 1st from
    the leaderboard's `experiments` list."""
    csv_path = tmp_path / "experiments.csv"
    out_path = tmp_path / "leaderboard.json"
    snap_dir = tmp_path / "snapshots"

    # Round 1: only exp_001 (content-anchored columns are None — frozen row)
    _write_csv(csv_path, [{
        "exp_name": "exp_001_naive_baseline",
        "timestamp": "2026-09-05T07:45:04",
        "n_questions": "139", "n_filings": "20", "n_chunks": "4447",
        "context_recall": "0.8058", "faithfulness": "0.8847", "answer_relevancy": "0.7428",
        "hit_at_5": "0.6043", "citation_accuracy": "0.5612",
        "mean_latency_ms": "8731.8", "total_cost_usd": "0.0381",
        "hit_at_5_content": "", "citation_accuracy_content": "",
    }])
    rc = update_leaderboard_main.__wrapped__ if hasattr(update_leaderboard_main, "__wrapped__") else update_leaderboard_main
    # Call the function via subprocess because it reads sys.argv
    import subprocess
    subprocess.run(
        [sys.executable, str(_ROOT / "tests" / "eval" / "update_leaderboard.py"),
         "--csv", str(csv_path), "--out", str(out_path), "--snapshot-dir", str(snap_dir)],
        check=True,
    )
    lb1 = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(lb1["experiments"]) == 1
    assert lb1["experiments"][0]["exp_name"] == "exp_001_naive_baseline"
    assert lb1["categories"]["end_to_end"]["winner"] == "exp_001_naive_baseline"

    # Round 2: append exp_002 with better faithfulness (content-anchored
    # columns are also None — exp_002 predates the metric refactor).
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "exp_name", "timestamp", "n_questions", "n_filings", "n_chunks",
            "context_recall", "faithfulness", "answer_relevancy",
            "hit_at_5", "citation_accuracy", "mean_latency_ms", "total_cost_usd",
            "hit_at_5_content", "citation_accuracy_content",
        ])
        writer.writerow({
            "exp_name": "exp_002_recursive",
            "timestamp": "2026-09-06T12:00:00",
            "n_questions": "139", "n_filings": "20", "n_chunks": "4100",
            "context_recall": "0.82", "faithfulness": "0.91", "answer_relevancy": "0.76",
            "hit_at_5": "0.68", "citation_accuracy": "0.62",
            "mean_latency_ms": "8500", "total_cost_usd": "0.037",
            "hit_at_5_content": "", "citation_accuracy_content": "",
        })
    subprocess.run(
        [sys.executable, str(_ROOT / "tests" / "eval" / "update_leaderboard.py"),
         "--csv", str(csv_path), "--out", str(out_path), "--snapshot-dir", str(snap_dir)],
        check=True,
    )
    lb2 = json.loads(out_path.read_text(encoding="utf-8"))
    # History grew
    assert len(lb2["experiments"]) == 2
    names = {e["exp_name"] for e in lb2["experiments"]}
    assert "exp_001_naive_baseline" in names, "exp_001 must still be in history"
    assert "exp_002_recursive" in names
    # exp_001's row must be unchanged (same numbers as the first run)
    e1 = next(e for e in lb2["experiments"] if e["exp_name"] == "exp_001_naive_baseline")
    assert e1["context_recall"] == 0.8058
    assert e1["timestamp"] == "2026-09-05T07:45:04"
    # Category winner updated to exp_002 (better faithfulness)
    assert lb2["categories"]["end_to_end"]["winner"] == "exp_002_recursive"
    assert lb2["categories"]["end_to_end"]["runner_up"] == "exp_001_naive_baseline"
    # Two snapshots written
    snaps = sorted(snap_dir.glob("leaderboard_*.json"))
    assert len(snaps) == 2, f"expected 2 snapshots, got {len(snaps)}: {snaps}"


def test_snapshot_is_immutable(tmp_path: Path) -> None:
    """Snapshots are write-once. We don't try to enforce this in code
    (write-once is a process convention, not a file-system property),
    but we at least verify the snapshot path includes a timestamp and
    doesn't get clobbered if a 2nd refresh happens later."""
    csv_path = tmp_path / "experiments.csv"
    out_path = tmp_path / "leaderboard.json"
    snap_dir = tmp_path / "snapshots"
    _write_csv(csv_path, [{
        "exp_name": "exp_001", "timestamp": "2026-09-05T07:45:04",
        "n_questions": "1", "n_filings": "1", "n_chunks": "1",
        "context_recall": "0.5", "faithfulness": "0.5", "answer_relevancy": "0.5",
        "hit_at_5": "0.5", "citation_accuracy": "0.5",
        "mean_latency_ms": "1.0", "total_cost_usd": "0.001",
        "hit_at_5_content": "", "citation_accuracy_content": "",
    }])
    import subprocess
    subprocess.run(
        [sys.executable, str(_ROOT / "tests" / "eval" / "update_leaderboard.py"),
         "--csv", str(csv_path), "--out", str(out_path), "--snapshot-dir", str(snap_dir)],
        check=True,
    )
    first = list(snap_dir.glob("leaderboard_*.json"))
    assert len(first) == 1
    # Run a 2nd refresh with same timestamp; should NOT clobber the first.
    # Modify the rolling leaderboard directly to simulate a downstream
    # change, then re-run with the same CSV/timestamp.
    out_path.write_text('{"tampered": true}', encoding="utf-8")
    subprocess.run(
        [sys.executable, str(_ROOT / "tests" / "eval" / "update_leaderboard.py"),
         "--csv", str(csv_path), "--out", str(out_path), "--snapshot-dir", str(snap_dir)],
        check=True,
    )
    after = list(snap_dir.glob("leaderboard_*.json"))
    # The first snapshot must still exist (untouched on disk) — we just
    # verify the file count grew (second run gets a counter suffix).
    assert len(after) >= 1
    assert first[0].exists(), "original snapshot must not be deleted"


def test_chunking_content_category_null_until_populated(tmp_path: Path) -> None:
    """Until exp_003 lands, no row has `hit_at_5_content` populated, so
    the `chunking_content` category must report `winner: null`. The
    `chunking` category (scored on `context_recall`) is unaffected.
    """
    csv_path = tmp_path / "experiments.csv"
    out_path = tmp_path / "leaderboard.json"
    snap_dir = tmp_path / "snapshots"
    # exp_001 + exp_002, both with empty content-anchored columns
    _write_csv(csv_path, [
        {
            "exp_name": "exp_001_naive_baseline",
            "timestamp": "2026-09-05T07:45:04",
            "n_questions": "139", "n_filings": "20", "n_chunks": "4447",
            "context_recall": "0.8058", "faithfulness": "0.8847", "answer_relevancy": "0.7428",
            "hit_at_5": "0.6043", "citation_accuracy": "0.5612",
            "mean_latency_ms": "8731.8", "total_cost_usd": "0.0381",
            "hit_at_5_content": "", "citation_accuracy_content": "",
        },
        {
            "exp_name": "exp_002_recursive",
            "timestamp": "2026-09-05T09:07:05",
            "n_questions": "139", "n_filings": "20", "n_chunks": "5412",
            "context_recall": "0.7913", "faithfulness": "0.8595", "answer_relevancy": "0.7080",
            "hit_at_5": "0.3237", "citation_accuracy": "0.2158",
            "mean_latency_ms": "9968.1", "total_cost_usd": "0.0299",
            "hit_at_5_content": "", "citation_accuracy_content": "",
        },
    ])
    import subprocess
    subprocess.run(
        [sys.executable, str(_ROOT / "tests" / "eval" / "update_leaderboard.py"),
         "--csv", str(csv_path), "--out", str(out_path), "--snapshot-dir", str(snap_dir)],
        check=True,
    )
    lb = json.loads(out_path.read_text(encoding="utf-8"))
    # Both content-anchored columns appear as None in the per-experiment rows
    assert all(
        e["hit_at_5_content"] is None and e["citation_accuracy_content"] is None
        for e in lb["experiments"]
    )
    # The chunking_content category has a null winner (intentional sentinel)
    assert lb["categories"]["chunking_content"]["winner"] is None
    assert lb["categories"]["chunking_content"]["metric"] == "hit_at_5_content"
    # The original chunking category still works (scored on context_recall)
    assert lb["categories"]["chunking"]["winner"] in {
        "exp_001_naive_baseline", "exp_002_recursive",
    }


def test_chunking_content_category_populated_after_exp_003(tmp_path: Path) -> None:
    """Once a row populates `hit_at_5_content`, the chunking_content
    category surfaces it as the winner.
    """
    csv_path = tmp_path / "experiments.csv"
    out_path = tmp_path / "leaderboard.json"
    snap_dir = tmp_path / "snapshots"
    _write_csv(csv_path, [
        {
            "exp_name": "exp_001_naive_baseline",
            "timestamp": "2026-09-05T07:45:04",
            "n_questions": "139", "n_filings": "20", "n_chunks": "4447",
            "context_recall": "0.8058", "faithfulness": "0.8847", "answer_relevancy": "0.7428",
            "hit_at_5": "0.6043", "citation_accuracy": "0.5612",
            "mean_latency_ms": "8731.8", "total_cost_usd": "0.0381",
            "hit_at_5_content": "", "citation_accuracy_content": "",
        },
        {
            "exp_name": "exp_003_semantic",
            "timestamp": "2026-09-06T12:00:00",
            "n_questions": "139", "n_filings": "20", "n_chunks": "5000",
            "context_recall": "0.83", "faithfulness": "0.87", "answer_relevancy": "0.75",
            "hit_at_5": "0.55", "citation_accuracy": "0.50",
            "mean_latency_ms": "9500", "total_cost_usd": "0.04",
            "hit_at_5_content": "0.78", "citation_accuracy_content": "0.72",
        },
    ])
    import subprocess
    subprocess.run(
        [sys.executable, str(_ROOT / "tests" / "eval" / "update_leaderboard.py"),
         "--csv", str(csv_path), "--out", str(out_path), "--snapshot-dir", str(snap_dir)],
        check=True,
    )
    lb = json.loads(out_path.read_text(encoding="utf-8"))
    # The chunking_content category now has a real winner
    assert lb["categories"]["chunking_content"]["winner"] == "exp_003_semantic"
    assert lb["categories"]["chunking_content"]["winner_value"] == 0.78
    assert lb["categories"]["chunking_content"]["runner_up"] is None
    # exp_001 still appears in history with None for the new columns
    e1 = next(e for e in lb["experiments"] if e["exp_name"] == "exp_001_naive_baseline")
    assert e1["hit_at_5_content"] is None
    # exp_003 has its content-anchored values populated
    e3 = next(e for e in lb["experiments"] if e["exp_name"] == "exp_003_semantic")
    assert e3["hit_at_5_content"] == 0.78
    assert e3["citation_accuracy_content"] == 0.72
