"""Nightly drift check (STEP_027).

Compares a fresh candidate row (smoke or full-run CSV) against a frozen
ledger baseline and fails loudly on regressions. Designed for schedulers
(Task Scheduler / cron) that key off the exit code:

    uv run python scripts/check_drift.py \
        --ledger results/experiments.csv \
        --baseline-exp exp_021_hybrid_rrf \
        --candidate results/smoke/<run>/smoke_experiments.csv

Exit 0 = within tolerance (prints JSON verdict). Exit 1 = breach (prints
JSON, optionally appends to --alert-log). Exit 2 = usage/data error.

Rules (locked with the ledger's spirit):
- Metrics compared both directions with --tol (default 0.05): a drop
  beyond tol breaches; a jump beyond tol is reported as info, not breach
  (improvements are welcome — they just don't fail the night).
- Small-n guard (STEP_027 lesson): each Q in a 10-Q smoke is 10pp, so a
  flat tol false-alarms. The effective threshold is
  max(tol, 1.96 * sqrt(p * (1-p) / n_candidate)) with p the baseline
  value — the 95% binomial noise floor. Full runs (n=139) are unaffected
  in practice (floor ≈ 0.04-0.08 ≈ tol); smokes stop crying wolf.
- Empty/None on either side SKIPS the metric (frozen exp_001/002 rows
  lack content columns; future columns must not break old baselines).
- Latency breaches when candidate > --latency-factor x baseline (default
  2.0). Missing latency on either side skips.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

COMPARED_METRICS = [
    "context_recall",
    "faithfulness",
    "answer_relevancy",
    "hit_at_5",
    "citation_accuracy",
    "hit_at_5_content",
    "citation_accuracy_content",
]


def _num(value: str | None) -> float | None:
    if value is None or value == "" or value == "None":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _noise_floor(baseline_p: float, n_candidate: int) -> float:
    """95% binomial noise floor for a [0,1] mean over n_candidate Q's."""
    import math

    if n_candidate <= 0:
        return 1.0
    p = max(0.0, min(1.0, baseline_p))
    return 1.96 * math.sqrt(p * (1.0 - p) / n_candidate)


def _last_row(csv_path: Path) -> dict[str, str]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No data rows in {csv_path}")
    return rows[-1]


def _resolve_candidate(candidate: Path) -> Path:
    """Accept a CSV file or a directory holding run outputs.

    Smoke mode writes timestamped dirs (`results/smoke/<exp>_<ts>/`), which
    accumulate night after night — resolving the newest `smoke_experiments.csv`
    here keeps scheduler recipes (and humans) from globbing.
    """
    if candidate.is_dir():
        cands = sorted(candidate.glob("*/smoke_experiments.csv"),
                       key=lambda p: p.stat().st_mtime)
        if not cands:
            raise ValueError(f"No smoke_experiments.csv under {candidate}")
        return cands[-1]
    return candidate


def _baseline_row(ledger_path: Path, exp_name: str) -> dict[str, str]:
    with ledger_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("exp_name") == exp_name:
                return row
    raise ValueError(f"Baseline {exp_name!r} not found in {ledger_path}")


def check_drift(baseline: dict[str, str], candidate: dict[str, str],
                tol: float = 0.05, latency_factor: float = 2.0,
                n_candidate: int | None = None) -> dict:
    """Pure comparison. Returns a JSON-serializable verdict dict.

    `n_candidate` (default: read from candidate["n_questions"], fallback
    139) sets the binomial noise floor: the effective per-metric
    threshold is max(tol, floor), so 10-Q smokes aren't judged by
    full-run precision.
    """
    compared: dict[str, dict] = {}
    breaches: list[str] = []
    improvements: list[str] = []
    if n_candidate is None:
        try:
            n_candidate = int(float(candidate.get("n_questions") or 139))
        except (TypeError, ValueError):
            n_candidate = 139
    for metric in COMPARED_METRICS:
        b, c = _num(baseline.get(metric)), _num(candidate.get(metric))
        if b is None or c is None:
            compared[metric] = {"baseline": b, "candidate": c, "status": "skipped"}
            continue
        threshold = max(tol, _noise_floor(b, n_candidate))
        delta = c - b
        if delta < -threshold:
            status = "BREACH"
            breaches.append(
                f"{metric}: {b:.4f} -> {c:.4f} "
                f"(delta {delta:+.4f} < -{threshold:.4f})")
        else:
            status = "ok"
            if delta > threshold:
                improvements.append(f"{metric}: {b:.4f} -> {c:.4f} (delta {delta:+.4f})")
        compared[metric] = {"baseline": b, "candidate": c,
                            "delta": round(delta, 4),
                            "threshold": round(threshold, 4),
                            "status": status}
    lat_status = "skipped"
    bl, cl = _num(baseline.get("mean_latency_ms")), _num(candidate.get("mean_latency_ms"))
    if bl is not None and cl is not None and bl > 0:
        if cl > latency_factor * bl:
            lat_status = "BREACH"
            breaches.append(f"mean_latency_ms: {bl:.0f} -> {cl:.0f} (> {latency_factor}x)")
        else:
            lat_status = "ok"
    return {"ok": not breaches, "breaches": breaches,
            "improvements": improvements, "metrics": compared,
            "latency_status": lat_status,
            "baseline_exp": baseline.get("exp_name"),
            "candidate_exp": candidate.get("exp_name")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=Path("results/experiments.csv"))
    parser.add_argument("--baseline-exp", default="exp_021_hybrid_rrf")
    parser.add_argument("--candidate", type=Path, required=True,
                        help="CSV holding the fresh row (last row is compared), "
                             "or a directory of smoke runs (newest is used)")
    parser.add_argument("--tol", type=float, default=0.05)
    parser.add_argument("--latency-factor", type=float, default=2.0)
    parser.add_argument("--alert-log", type=Path, default=None,
                        help="Append JSONL breach records here (breaches only)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write the verdict JSON here as well as stdout")
    args = parser.parse_args()

    for path in (args.ledger, args.candidate):
        if not path.exists():
            print(f"[DRIFT-ERROR] file not found: {path}", file=sys.stderr)
            return 2
    try:
        baseline = _baseline_row(args.ledger, args.baseline_exp)
        candidate = _last_row(_resolve_candidate(args.candidate))
    except ValueError as e:
        print(f"[DRIFT-ERROR] {e}", file=sys.stderr)
        return 2

    verdict = check_drift(baseline, candidate, tol=args.tol,
                          latency_factor=args.latency_factor)
    text = json.dumps(verdict, indent=2)
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    if not verdict["ok"]:
        print(f"[DRIFT-BREACH] {len(verdict['breaches'])} breach(es) "
              f"vs {args.baseline_exp}", file=sys.stderr)
        if args.alert_log is not None:
            args.alert_log.parent.mkdir(parents=True, exist_ok=True)
            with args.alert_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**verdict, "baseline_exp": args.baseline_exp}) + "\n")
        return 1
    print(f"[DRIFT-OK] within tolerance of {args.baseline_exp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
