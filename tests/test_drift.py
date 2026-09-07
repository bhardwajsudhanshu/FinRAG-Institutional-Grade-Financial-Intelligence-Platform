"""Unit tests for scripts/check_drift.py (STEP_027). Fully offline."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

# repo root for imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

sys.path.insert(0, str(_ROOT / "scripts"))
from check_drift import check_drift


def _row(**over) -> dict:
    base = {"exp_name": "exp_x", "context_recall": "0.80", "faithfulness": "0.88",
            "answer_relevancy": "0.74", "hit_at_5": "0.60",
            "citation_accuracy": "0.56", "hit_at_5_content": "0.70",
            "citation_accuracy_content": "0.65", "mean_latency_ms": "8000",
            "total_cost_usd": "0.03"}
    base.update(over)
    return base


class TestNoDrift:
    def test_identical_rows_pass(self) -> None:
        v = check_drift(_row(), _row())
        assert v["ok"] is True
        assert v["breaches"] == []

    def test_noise_within_tol_passes(self) -> None:
        v = check_drift(_row(), _row(context_recall="0.79", faithfulness="0.90"))
        assert v["ok"] is True

    def test_improvement_is_info_not_breach(self) -> None:
        v = check_drift(_row(), _row(context_recall="0.90"))
        assert v["ok"] is True
        assert len(v["improvements"]) == 1


class TestBreach:
    def test_drop_beyond_tol_breaches(self) -> None:
        v = check_drift(_row(), _row(hit_at_5_content="0.60"))
        assert v["ok"] is False
        assert any("hit_at_5_content" in b for b in v["breaches"])

    def test_latency_spike_breaches(self) -> None:
        v = check_drift(_row(), _row(mean_latency_ms="20000"))
        assert v["ok"] is False
        assert any("latency" in b for b in v["breaches"])

    def test_latency_within_factor_passes(self) -> None:
        v = check_drift(_row(), _row(mean_latency_ms="15000"))
        assert v["ok"] is True
        assert v["latency_status"] == "ok"


class TestSkips:
    def test_missing_on_either_side_skips(self) -> None:
        # Frozen exp_001/002 rows lack content columns (empty strings).
        v = check_drift(_row(hit_at_5_content=""), _row(hit_at_5_content="0.70"))
        assert v["ok"] is True
        assert v["metrics"]["hit_at_5_content"]["status"] == "skipped"

    def test_missing_latency_skips(self) -> None:
        v = check_drift(_row(mean_latency_ms=""), _row())
        assert v["ok"] is True
        assert v["latency_status"] == "skipped"

    def test_garbage_values_skip(self) -> None:
        v = check_drift(_row(), _row(context_recall="n/a"))
        assert v["ok"] is True
        assert v["metrics"]["context_recall"]["status"] == "skipped"


class TestNoiseFloor:
    """STEP_027 lesson: 10-Q smokes must not be judged by full-run precision."""

    def test_small_n_forgives_noise(self) -> None:
        base = _row(n_questions="139")
        cand = _row(n_questions="10", hit_at_5="0.60")  # -0.076 vs 0.676 floor
        v = check_drift(base, cand)
        assert v["ok"] is True
        assert v["metrics"]["hit_at_5"]["status"] == "ok"

    def test_large_n_still_binds(self) -> None:
        base = _row(n_questions="139")
        cand = _row(n_questions="139", hit_at_5="0.50")  # -0.10 < floor ~0.082
        v = check_drift(base, cand)
        assert v["ok"] is False

    def test_real_collapse_still_breaches_at_small_n(self) -> None:
        base = _row(n_questions="139")
        cand = _row(n_questions="10", hit_at_5="0.20")  # -0.476 >> floor ~0.29
        v = check_drift(base, cand)
        assert v["ok"] is False

    def test_explicit_n_candidate_overrides(self) -> None:
        base = _row()
        cand = _row(hit_at_5="0.60")
        v = check_drift(base, cand, n_candidate=10)
        assert v["ok"] is True


class TestCli:
    def test_cli_exit_codes(self, tmp_path: Path) -> None:
        import subprocess

        ledger = tmp_path / "ledger.csv"
        cand = tmp_path / "cand.csv"
        fields = ["exp_name", "context_recall", "faithfulness", "answer_relevancy",
                  "hit_at_5", "citation_accuracy", "hit_at_5_content",
                  "citation_accuracy_content", "mean_latency_ms", "total_cost_usd"]
        for path, rows in ((ledger, [_row(exp_name="base")]), (cand, [_row(exp_name="night")])):
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(rows)
        r = subprocess.run(
            [sys.executable, str(_ROOT / "scripts" / "check_drift.py"),
             "--ledger", str(ledger), "--baseline-exp", "base",
             "--candidate", str(cand)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "DRIFT-OK" in r.stdout


class TestResolveCandidate:
    def test_file_passes_through(self, tmp_path: Path) -> None:
        from check_drift import _resolve_candidate

        f = tmp_path / "a.csv"
        f.write_text("x", encoding="utf-8")
        assert _resolve_candidate(f) == f

    def test_directory_picks_newest(self, tmp_path: Path) -> None:
        import time

        from check_drift import _resolve_candidate

        old = tmp_path / "run_old"
        new = tmp_path / "run_new"
        old.mkdir()
        (old / "smoke_experiments.csv").write_text("old", encoding="utf-8")
        time.sleep(0.02)
        new.mkdir()
        (new / "smoke_experiments.csv").write_text("new", encoding="utf-8")
        assert _resolve_candidate(tmp_path) == new / "smoke_experiments.csv"

    def test_empty_directory_errors(self, tmp_path: Path) -> None:
        from check_drift import _resolve_candidate

        with pytest.raises(ValueError):
            _resolve_candidate(tmp_path)
