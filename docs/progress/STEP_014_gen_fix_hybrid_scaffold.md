# STEP_014 — Generation multi-part fix + exp_021 hybrid scaffold

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Kill the exp_020 q_0053 failure class; scaffold the hybrid run. No ledger change.
- **Roadmap phase:** Week 5-8 Retrieval (robustness + exp_021 ready)

### 1. Why
Two unrelated items, one step (both small, both block STEP_015):
(a) exp_020's only generation failure — Flash returned 2 identical parts
and SDK `.text` raised. 1/139 today, but nightly runs + bigger eval sets
multiply the exposure. (b) exp_021 hybrid needs its scaffold + smoke before
the ~50-min full run.

### 2. What changed (files — this commit)
- `finrag/generation.py` — NEW `_response_text()` (try `.text`, fall back to joining all text parts across candidates, `""` if none) + `VertexGenerator.generate` uses it. Normal path byte-identical (`.text` still first).
- `tests/test_generation.py` — NEW, 6 tests (single/multi/empty/mixed-part stubs via ClassVar duck-types; MockGenerator refuse + cite contracts).
- `docs/experiments/exp_021_hybrid_rrf/{README,config.yaml,analysis.md}` — NEW scaffold (both-bars hypothesis, frozen RRF params, smoke filled).
- `docs/progress/STEP_014_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (5 rows), leaderboard, eval set, runner, retrieval math.
- NOT committed: `results/smoke/exp_021_hybrid_rrf_*/` (ephemeral).

### 3. How it works
`_response_text` catches *any* `.text` exception (SDK raises ValueError
today; no reason to couple to its message), warns once via loguru, then
walks `candidates → content.parts → .text`, skipping non-text/None parts.
Empty result → `""` → runner's existing empty-answer path (same as the old
except-branch produced, minus the lost answer — multi-part answers now
survive instead of voiding).

### 4. How to verify
```bash
uv run pytest tests/test_generation.py tests/test_retrieval.py tests/test_chunking.py tests/eval/test_metrics.py tests/eval/test_ragas_runner.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid uv run python -m finrag.cli.eval --exp exp_021_hybrid_rrf --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 85 passed (6 new). Ruff: own RUF012s fixed via ClassVar; remaining flag (E402 sys.path pattern) shared by all test files, pre-existing.
- Smoke 2026-09-07 (6 Q, AAPL naive 97 chunks, $0.0017): content 0.833 (5/6, only miss q_0005 — missed by every strategy), cr=1.0/fa=1.0, index 18.9s. No signal at n=6 by design.
- PowerShell note (own mistake, recorded): heredoc `<<EOF` doesn't exist in PS 5.1 — use edit/write tools for file ops, never shell redirection.

### 6. How to recall
- STEP file: `docs/progress/STEP_014_gen_fix_hybrid_scaffold.md`
- Code: `finrag/generation.py::_response_text`; tests: `tests/test_generation.py`
- Failure it fixes: `results/exp_020_bm25/per_question.jsonl` q_0053 row (empty answer) + STEP_013 §3 log excerpt
- Exp: `docs/experiments/exp_021_hybrid_rrf/`

### 7. Next step (STEP_015)
Full exp_021 hybrid run (`CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid`, ~50 min — dense-side embedding returns) → both-bars verdict → leaderboard. Bars: hit@5_content > 0.7194 AND context_recall > 0.8058.
