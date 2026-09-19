"""Unit tests for scripts/readme_table.py (STEP_042). Fully offline."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# tests/ -> project root, scripts/ for the module
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

from readme_table import (  # noqa: E402
    count_tests,
    load_ledger,
    render_counts,
    render_table,
    update_readme,
)


def _ledger(rows: list[dict], path: Path) -> Path:
    fields = ["exp_name", "context_recall", "faithfulness",
              "hit_at_5_content", "citation_accuracy"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def _row(name: str, cr: str, fa: str, hit: str, cite: str) -> dict:
    return {"exp_name": name, "context_recall": cr, "faithfulness": fa,
            "hit_at_5_content": hit, "citation_accuracy": cite}


class TestLoadLedger:
    def test_unknown_exp_raises_loudly(self, tmp_path: Path) -> None:
        p = _ledger([_row("exp_999_mystery", "0.5", "0.5", "0.5", "0.5")],
                    tmp_path / "exp.csv")
        try:
            load_ledger(p)
            raise AssertionError("should have raised")
        except KeyError as e:
            assert "EXP_META" in str(e)


class TestRenderTable:
    def test_unique_maxima_bolded(self, tmp_path: Path) -> None:
        p = _ledger([
            _row("exp_001_naive_baseline", "0.80", "0.88", "", "0.56"),
            _row("exp_021_hybrid_rrf", "0.88", "0.90", "0.81", "0.61"),
        ], tmp_path / "exp.csv")
        table = render_table(load_ledger(p))
        assert "**0.9000**" in table  # unique max faithfulness
        assert "| **exp_021 hybrid RRF** |" in table  # leads all four

    def test_tied_maxima_stay_plain(self, tmp_path: Path) -> None:
        p = _ledger([
            _row("exp_021_hybrid_rrf", "0.88", "0.90", "0.81", "0.61"),
            _row("exp_022_hybrid_qdrant", "0.87", "0.89", "0.81", "0.61"),
        ], tmp_path / "exp.csv")
        table = render_table(load_ledger(p))
        assert "**0.8100**" not in table  # tied hit@5_content: no false winner

    def test_none_renders_em_dash(self, tmp_path: Path) -> None:
        p = _ledger([_row("exp_001_naive_baseline", "0.80", "0.88", "", "0.56")],
                    tmp_path / "exp.csv")
        table = render_table(load_ledger(p))
        assert "—" in table


class TestCounts:
    def test_counts_functions_plus_parametrize(self, tmp_path: Path) -> None:
        d = tmp_path / "tests"
        d.mkdir()
        (d / "test_a.py").write_text(
            "import pytest\n"
            "\n"
            "def test_one(): pass\n"
            "\n"
            "@pytest.mark.parametrize('x', [1, 2, 3])\n"
            "def test_many(x): pass\n", encoding="utf-8")
        assert count_tests(d) == 4

    def test_broken_files_skipped(self, tmp_path: Path) -> None:
        d = tmp_path / "tests"
        d.mkdir()
        (d / "test_a.py").write_text("def test_one(): pass\n", encoding="utf-8")
        (d / "test_b.py").write_text("def broken(:\n", encoding="utf-8")
        assert count_tests(d) == 1

    def test_render_counts(self) -> None:
        assert render_counts(13, 191) == "13 benchmarked experiments, 191 tests"


class TestUpdateReadme:
    def _readme(self, path: Path) -> Path:
        path.write_text(
            "head 3 benchmarked experiments, 7 tests tail\n"
            "<!-- RESULTS:START -->\nOLD TABLE\n<!-- RESULTS:END -->\nfoot\n",
            encoding="utf-8")
        return path

    def test_rewrites_section_and_counts(self, tmp_path: Path) -> None:
        r = self._readme(tmp_path / "README.md")
        new_text, changed = update_readme(r, "NEW TABLE\n", "13 benchmarked experiments, 191 tests")
        assert changed is True
        assert "NEW TABLE" in new_text
        assert "13 benchmarked experiments, 191 tests" in new_text
        assert "OLD TABLE" not in new_text

    def test_second_run_is_idempotent(self, tmp_path: Path) -> None:
        r = self._readme(tmp_path / "README.md")
        new_text, _ = update_readme(r, "NEW TABLE\n", "13 benchmarked experiments, 191 tests")
        r.write_text(new_text, encoding="utf-8")
        _, changed = update_readme(r, "NEW TABLE\n", "13 benchmarked experiments, 191 tests")
        assert changed is False

    def test_missing_markers_raise(self, tmp_path: Path) -> None:
        r = tmp_path / "README.md"
        r.write_text("no markers here\n", encoding="utf-8")
        try:
            update_readme(r, "X\n", "1 benchmarked experiments, 1 tests")
            raise AssertionError("should have raised")
        except ValueError as e:
            assert "Markers" in str(e)
