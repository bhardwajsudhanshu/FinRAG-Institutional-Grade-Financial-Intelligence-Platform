# STEP_034 — Multi-query expansion + exp_043 scaffold (smoke 6/6)

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** Question-side expansion becomes an orthogonal flag; exp_043 isolates it vs exp_001. No ledger change.
- **Roadmap phase:** Retrieval leftovers (last untested family: question-side)

### 1. Why
All gains so far are document-side (chunks) or ranking-side (fusion,
rerank). Vocabulary mismatch lives on the QUESTION side — no experiment
has touched it. Multi-query is the cheapest question-side idea with a
clean ablation (expansion on/off, everything else identical).
(No new ADR: orthogonal-flag design follows the rerank precedent;
stack-level decisions unchanged.)

### 2. What changed (files — this commit)
- `finrag/multiquery.py` — NEW `QueryExpander` (Flash JSON paraphrases, temp 0.7 for diversity, failure → [] never raises; injectable `generate_fn`) + `multi_query_retrieve()` (fuse FINAL per-query rankings — strategy-agnostic by construction — deterministic tie-breaks).
- `finrag/config.py` — `multiquery_enabled=False` + `multiquery_paraphrases=3`.
- `finrag/eval/ragas_runner.py` — expander built once (client reuse); per-Q expand→fuse→rerank chain; per-Q `multiquery` field.
- `finrag/cli/eval.py` — prints `Multiquery:` line.
- `tests/test_multiquery.py` — NEW, 8 tests (expansion hygiene, single-query equivalence, paraphrase recall, dedup/top_k, determinism, factories).
- `docs/experiments/exp_043_multi_query/{README,config.yaml,analysis.md}` — NEW scaffold (one-variable-vs-exp_001 design).
- `docs/progress/STEP_034_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (11 rows), leaderboard, eval set, all strategies.
- NOT committed: `results/smoke/exp_043_multi_query_*/` (ephemeral).

### 3. How it works
`multiquery_enabled` on: per Q, Flash writes 3 paraphrases → each formulation retrieved via `retrieve_with_strategy` (any base strategy) → RRF fuse → top-5 → rerank chain unchanged. Off: zero extra calls, byte-identical path. Fusion over final rankings means hybrid-parent etc. compose free.

### 4. How to verify
```bash
uv run pytest tests/test_multiquery.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=dense MULTIQUERY_ENABLED=true VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_043_multi_query --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 8 passed. During-step correction, recorded: first `multi_query_retrieve` draft special-cased hybrid-parent remapping (duplicated dispatcher logic + dead lines) — rewritten to fuse final rankings, half the code, zero special cases. Simpler > closer-to-metal.
- Ruff: own UP035/RUF005 fixed; rest pre-existing.
- Smoke 2026-09-08 (6 Q, AAPL naive 97, $0.0017): content **1.000 (6/6, third ever — q_0005 True)**, ~19s/Q (expansion + 4× retrievals). AAPL slice saturated — full run + concentration analysis is the whole verdict.

### 6. How to recall
- STEP file: `docs/progress/STEP_034_multi_query_expansion.md`
- Code: `finrag/multiquery.py`; tests: `tests/test_multiquery.py`
- Exp: `docs/experiments/exp_043_multi_query/`
- Proof: `results/smoke/exp_043_multi_query_20260908_102254/` (untracked)

### 7. Next step (STEP_035)
Full exp_043 run (~55 min: base + 139 expansion calls) → gain-concentration verdict vs exp_001 (0.6043) + cost note → leaderboard. If gains scatter uniformly, expansion is noise (retire); if they concentrate in lexical-gap Q's, it's a real (if small) lever.
