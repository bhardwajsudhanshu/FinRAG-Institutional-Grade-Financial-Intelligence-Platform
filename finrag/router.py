"""Heuristic retrieval router (STEP_046) — cheap rules, measured honestly.

`route_question` picks one of dense/bm25/hybrid per question. The routing
eval (`tests/eval/evaluate_router.py`) scores it OFFLINE against frozen
per-Q JSONLs: oracle upper bound, hybrid-always baseline, heuristic.
No Vertex, no Docker, $0 — routing quality is a data question, not a
model question.

Deliberate non-goals: learned routers, per-Q embeddings, confidence
thresholds. If the heuristic cannot beat hybrid-always, it ships nothing
(same bar as MiniLM/multiquery: measured, then retired or filed).
"""

from __future__ import annotations

import re

STRATEGIES = ("dense", "bm25", "hybrid")

_ITEM_REF = re.compile(r"\bitem\s+\d+[a-z]?\b")


def route_question(question: str, qa_type: str = "") -> str:
    """Return a retrieval strategy for one question.

    v1 rules (a priori, from retrieval intuition — see evaluate_router.py
    for the per-qa_type table that motivated them):
    - out-of-scope: bm25. Lexical, embeds nothing; OOS success means the
      source chunk is NOT retrieved, and dense semantic reach is exactly
      what drags in near-miss distractors.
    - explicit item/section anchors ("item 1a", "section"): bm25. The
      anchor tokens are already the answer's address.
    - short lookups (<= 5 words): bm25. Entity/number questions live or
      die on exact terms.
    - everything else: hybrid (the sweep winner — default, not fallback).
    """
    q = question.lower()
    if qa_type.strip().lower() == "out-of-scope":
        return "bm25"
    if _ITEM_REF.search(q) or "section" in q:
        return "bm25"
    if len(q.split()) <= 5:
        return "bm25"
    return "hybrid"


def score_routing(per_q: dict[str, dict[str, dict[str, bool]]],
                  decisions: dict[str, str]) -> dict:
    """Score a routing decision set against joined per-Q outcomes.

    per_q: qid -> strategy -> {"hit": bool, "cite": bool}.
    decisions: qid -> strategy. Unknown qids / strategies raise KeyError
    (loud — silent drops would flatter the router).
    """
    hits = cites = 0
    oracle_hits = oracle_cites = 0
    n = len(decisions)
    if n == 0:
        raise ValueError("no routing decisions to score")
    for qid, strategy in decisions.items():
        outcomes = per_q[qid]  # KeyError if qid unknown
        chosen = outcomes[strategy]  # KeyError if strategy unknown
        hits += chosen["hit"]
        cites += chosen["cite"]
        oracle_hits += any(o["hit"] for o in outcomes.values())
        oracle_cites += any(o["cite"] for o in outcomes.values())
    return {"n": n, "hit_rate": hits / n, "cite_rate": cites / n,
            "oracle_hit_rate": oracle_hits / n,
            "oracle_cite_rate": oracle_cites / n}
