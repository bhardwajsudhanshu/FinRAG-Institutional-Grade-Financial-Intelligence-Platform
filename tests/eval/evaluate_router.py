"""Offline routing eval (STEP_046). $0, no Vertex, no Docker.

Joins frozen per-Q JSONLs for dense/bm25/hybrid on qid and reports:
1. per-strategy hit/cite rates, overall + per qa_type (the table that
   motivates — or kills — routing rules),
2. oracle upper bound (per-Q best strategy),
3. heuristic (`finrag.router.route_question`) vs hybrid-always.

Usage:
    uv run python tests/eval/evaluate_router.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from finrag.router import STRATEGIES, route_question, score_routing

FILES = {
    "dense": _ROOT / "results" / "exp_001_naive_baseline" / "per_question.jsonl",
    "bm25": _ROOT / "results" / "exp_020_bm25" / "per_question.jsonl",
    "hybrid": _ROOT / "results" / "exp_021_hybrid_rrf" / "per_question.jsonl",
}


def load_joined() -> tuple[dict, dict]:
    """Returns (per_q, qa_type): per_q[qid][strategy] = {hit, cite}.

    hit/cite are True/False/None — None means the frozen row predates the
    content metrics (exp_001-004), NOT a miss. Strategies without full
    coverage are reported and excluded from the verdict (comparing a
    measured rate against missing data would be fabrication).
    """
    per_q: dict[str, dict[str, dict]] = {}
    qa_type: dict[str, str] = {}
    for strategy, path in FILES.items():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                qid = row["qid"]
                per_q.setdefault(qid, {})[strategy] = {
                    "hit": row.get("hit_at_5_content"),  # may be None
                    "cite": row.get("citation_accuracy_content"),
                }
                qa_type[qid] = row.get("qa_type", "")
    # Frozen-set discipline: every strategy must cover every Q.
    short = {qid: sorted(v) for qid, v in per_q.items()
             if set(v) != set(STRATEGIES)}
    if short:
        raise ValueError(f"strategies missing Qs (showing 5): {dict(list(short.items())[:5])}")
    return per_q, qa_type


def _rate(vals: list) -> tuple[float, int]:
    measured = [v for v in vals if v is not None]
    if not measured:
        return float("nan"), 0
    return sum(measured) / len(measured), len(measured)


def main() -> int:
    per_q, qa_type = load_joined()
    n = len(per_q)
    print(f"joined Qs: {n}")

    # Coverage first — missing is missing, not zero.
    print("\n== content-metric coverage (measured Qs / 139) ==")
    verdict_strategies = []
    for s in STRATEGIES:
        _, cov_hit = _rate([per_q[q][s]["hit"] for q in per_q])
        _, cov_cite = _rate([per_q[q][s]["cite"] for q in per_q])
        print(f"{s:<8}hit coverage {cov_hit:>4}  cite coverage {cov_cite:>4}")
        if cov_hit == n and cov_cite == n:
            verdict_strategies.append(s)
    print(f"verdict strategies (full coverage): {verdict_strategies}")
    if len(verdict_strategies) < 2:
        raise ValueError("need >= 2 fully-covered strategies for a verdict")

    # 1. per-strategy x qa_type table (measured Qs only)
    types = sorted(set(qa_type.values()))
    print("\n== hit_rate by strategy x qa_type (measured only) ==")
    header = f"{'qa_type':<12}{'n':>5}" + "".join(f"{s:>10}" for s in STRATEGIES)
    print(header)
    for t in types:
        qids = [q for q in per_q if qa_type[q] == t]
        row = f"{t:<12}{len(qids):>5}"
        for s in STRATEGIES:
            rate, cov = _rate([per_q[q][s]["hit"] for q in qids])
            cell = f"{rate:.4f}" if cov else "no-data"
            row += f"{cell:>10}"
        print(row)
    overall = f"{'ALL':<12}{n:>5}"
    for s in STRATEGIES:
        rate, cov = _rate([v[s]["hit"] for v in per_q.values()])
        overall += f"{rate if cov else float('nan'):>10.4f}"
    print(overall)

    # 2+3. oracle + heuristic vs best single strategy, on fully-covered
    # strategies only. route_question may name dense; map unmeasurable
    # picks to hybrid (the default) and SAY so — no silent oracle help.
    sub = {qid: {s: {"hit": bool(o["hit"]), "cite": bool(o["cite"])}
                 for s, o in v.items() if s in verdict_strategies}
           for qid, v in per_q.items()}
    raw_decisions = {qid: route_question(_question(qid), qa_type[qid]) for qid in per_q}
    remapped = sum(1 for d in raw_decisions.values() if d not in verdict_strategies)
    decisions = {qid: (d if d in verdict_strategies else "hybrid")
                 for qid, d in raw_decisions.items()}
    routed = score_routing(sub, decisions)
    best_single = max(
        (score_routing(sub, dict.fromkeys(sub, s)) | {"strategy": s}
         for s in verdict_strategies),
        key=lambda r: r["hit_rate"])
    from collections import Counter
    print("\n== routing verdict ==")
    print(f"oracle:      hit={routed['oracle_hit_rate']:.4f} cite={routed['oracle_cite_rate']:.4f}")
    print(f"best-single ({best_single['strategy']}): hit={best_single['hit_rate']:.4f} cite={best_single['cite_rate']:.4f}")
    print(f"heuristic:   hit={routed['hit_rate']:.4f} cite={routed['cite_rate']:.4f}")
    print(f"route mix: {dict(Counter(decisions.values()))} "
          f"({remapped} dense picks remapped to hybrid: unmeasurable, not counted as wins)")
    return 0


def _question(qid: str) -> str:
    if not hasattr(_question, "_cache"):
        _question._cache = {}  # type: ignore[attr-defined]
        with FILES["hybrid"].open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    _question._cache[row["qid"]] = row["question"]  # type: ignore[attr-defined]
    return _question._cache[qid]  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
