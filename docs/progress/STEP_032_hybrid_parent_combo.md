# STEP_032 — Hybrid+parent combo + exp_042 scaffold (smoke 6/6)

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** Fuse in child space, generate from parents; scaffold the redemption arc. No ledger change.
- **Roadmap phase:** Retrieval leftovers (combo run will close or kill the hierarchy bet)

### 1. Why
exp_041 verdict: hierarchy helps (+9.4pp) but trails hybrid by 11pp —
hierarchy lacks lexical signal. exp_021 verdict: hybrid wins on parents.
The combo is the obvious child of both: BM25's exactness + dense's
breadth at child granularity, parents for generation. Single variable vs
each parent experiment.
(No new ADR: ADR-004's fusion framing covers it; stack unchanged.)

### 2. What changed (files — this commit)
- `finrag/retrieval.py` — `hybrid-parent` dispatch branch (dense top-20 children + BM25 top-20 children → RRF k=60 in child space → unique parents, best fused score → top-5; missing ids skipped). Hybrid branch verified intact after edit (re-read whole function — STEP_030 lesson applied).
- `finrag/eval/ragas_runner.py` — strategy validation + shared parent/child build path (`parent-doc`/`hybrid-parent` share chunking; BM25 side switches parents→children for hybrid-parent); bundle gains `children_by_id`; `n_chunks` stays parents (comparable).
- `finrag/config.py` — strategy comment documents `hybrid-parent`.
- `tests/test_parentdoc.py` — `TestHybridParent` (parents-not-children, dedup, unresolvable-ids-safe).
- `docs/experiments/exp_042_hybrid_parent/{README,config.yaml,analysis.md}` — NEW scaffold (two single-variable bars: >0.6978 AND >0.8129).
- `docs/progress/STEP_032_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (10 rows), leaderboard, eval set, dense/BM25/hybrid/parent-doc paths.
- NOT committed: `results/smoke/exp_042_hybrid_parent_*/` (ephemeral).

### 3. How it works
`build_index_for_qa_pairs(..., strategy="hybrid-parent")`: parents+children built once; dense slot = child index (embedded), bm25 slot = child BM25, `chunks_by_id` = parents + new `children_by_id`. Per Q: fuse child rankings → map → top-5 parents → generate. Rerank composes on top unchanged.

### 4. How to verify
```bash
uv run pytest tests/test_parentdoc.py tests/test_retrieval.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid-parent VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_042_hybrid_parent --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 39 passed (2 new combo tests). Ruff: pre-existing classes only.
- Smoke 2026-09-08 (6 Q, AAPL 97/280, $0.0016): content **1.000 (6/6, second ever — q_0005 True again)**, cr=1.0/fa=0.9714. Child-space fusion reproduces parent-doc's smoke exactly.
- Shared-dispatch edit discipline held: full-function re-read after edit, hybrid return verified byte-identical.

### 6. How to recall
- STEP file: `docs/progress/STEP_032_hybrid_parent_combo.md`
- Code: `finrag/retrieval.py` hybrid-parent branch; runner parent/child bundle
- Tests: `tests/test_parentdoc.py::TestHybridParent`
- Exp: `docs/experiments/exp_042_hybrid_parent/`
- Proof: `results/smoke/exp_042_hybrid_parent_20260908_085520/` (untracked)

### 7. Next step (STEP_033)
Full exp_042 run (~60 min, ~3× embed units) → both-bars verdict (>0.6978 AND >0.8129) + cost-per-point reckoning → leaderboard. If it clears both, hierarchy is redeemed and hybrid-parent becomes a serving option; if not, hierarchy retires (parent-doc stays a faithfulness footnote).
