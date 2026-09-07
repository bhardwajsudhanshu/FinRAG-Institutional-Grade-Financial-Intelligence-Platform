# STEP_022 — Rerank phase opens: ADR-006 + Flash pointwise + exp_030

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Ranking becomes a first-class axis (ADR-006); pointwise Flash scorer implemented, tested, smoke-verified. No ledger change.
- **Roadmap phase:** Rerank (opens; cheapest remaining quality lever per exp_001 forecast)

### 1. Why
Every row shows the recall↔citation gap (hybrid: 0.88 vs 0.61) — right
chunks retrieved, wrong ones ranked first. ADR-006 (written first) picks
pointwise Flash now, cross-encoder as deferred challenger, candidates=10
(cost/latency math inside), with a falsifiable success rule (citations
rise toward recall, recall doesn't drop — else it's a citer problem).

### 2. What changed (files — this commit)
- `docs/decisions/adr_006_rerank_direction.md` — NEW (order, pointwise rationale, 10-candidate math, falsifiability, exp_031 deferral).
- `finrag/rerank.py` — NEW `BaseReranker` (reorder-only contract: output keeps retrieval-scale scores), `NoopReranker`, `FlashPointwiseReranker` (JSON 0–10, retrieval-score-then-rank tie-break, unscored sink stably, `score_fn` injectable, lazy Vertex import), `get_reranker()`.
- `finrag/config.py` — `rerank_backend="none"` + `rerank_candidates=10`.
- `finrag/eval/ragas_runner.py` — construct once, `fetch_k` widened only when reranking (`none` keeps frozen width exactly), rerank inside the try, per-Q `reranker` field.
- `finrag/cli/eval.py` — prints `Rerank:` line.
- `tests/test_rerank.py` — NEW, 12 tests (noop, ordering, tie-breaks, sinking, truncation, score-scale, factory incl. monkeypatched settings).
- `docs/experiments/exp_030_flash_rerank/{README,config.yaml,analysis.md}` — NEW scaffold (one-variable-vs-exp_021 design, full command with all four env pins).
- `docs/progress/STEP_022_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (7 rows), leaderboard, eval set, retrieval math.
- NOT committed: `results/smoke/exp_030_flash_rerank_*/` (ephemeral).

### 3. How it works
`run_experiment`: fetch min(top_k, candidates)-widened list → `reranker.rerank(q, items, top_k)` → generate on top-5. Noop path is literally `items[:top_k]` — frozen rows reproducible to the item.

### 4. How to verify
```bash
uv run pytest tests/test_rerank.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid RERANK_BACKEND=flash-pointwise VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_030_flash_rerank --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 12 passed. One wrong test expectation fixed en route (mine: equal-score tie goes to higher retrieval score by design — test now asserts the designed behavior with comment). Ruff: own UP035 fixed (`collections.abc`); rest pre-existing.
- Smoke 2026-09-07 (6 Q, AAPL naive 97, 60 Flash calls, $0.0017): content 0.833 (5/6, only miss q_0005 — universal), cr=1.0/fa=0.975, ~36s/Q rerank overhead (confirms ~1.5h full-run estimate).
- First smoke attempt died instantly on machine-OS `VECTORDB_BACKEND=chroma` (STEP_020 trap — full-run commands must pin all four vars; README updated).
- During-step correction, recorded: rerank output keeps retrieval-scale scores (reorder-only contract) instead of my first draft's mixed 0–10/cosine scales.

### 6. How to recall
- STEP file: `docs/progress/STEP_022_rerank_flash_pointwise.md`
- Decision: `docs/decisions/adr_006_rerank_direction.md`
- Code: `finrag/rerank.py`; tests: `tests/test_rerank.py`
- Exp: `docs/experiments/exp_030_flash_rerank/`
- Proof: `results/smoke/exp_030_flash_rerank_20260907_105124/` (untracked)

### 7. Next step (STEP_023)
Full exp_030 run (~1.5h, ~$0.15 — most expensive yet, approved once) → gap verdict → leaderboard. Bars: citations rise toward 0.88 recall, recall non-decreasing.
