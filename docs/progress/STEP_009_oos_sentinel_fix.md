# STEP_009 — OOS sentinel normalization fix (no re-run)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Make `hit_at_5_content` honest for OOS Q's without touching the frozen eval set or ledger.
- **Roadmap phase:** Week 3-4 Chunking (methods hardening; applies from exp_004 onward)

### 1. Why
STEP_008 found all 18 OOS Q's score `hit_at_5_content=false` systematically:
the frozen v1 set stores `source_span="<no relevant span>"` (literal sentinel
written by the generator, `generate_qa_pairs.py:188-189`), but the runner's
OOS branch tests emptiness (`not source_span`). The sentinel is never empty,
so the branch never fires. Root doc mismatch: `_span_appears_in_chunk`'s
docstring claimed OOS spans are `""` — false for v1.

### 2. What changed (files — this commit)
- `finrag/eval/metrics.py` — NEW `OOS_SPAN_SENTINEL` + `normalize_source_span()`: None/blank/sentinel (stripped, exact) → `""`; all else passes through stripped-verbatim.
- `finrag/eval/__init__.py` — export it (`__all__` kept sorted).
- `finrag/eval/ragas_runner.py` — one-line wiring at read time (`run_experiment`: `source_span = normalize_source_span(...)`); OOS cite branch untouched (never used the span).
- `tests/eval/generate_qa_pairs.py` — comment-only: corrected the false `""`-by-design claim, points to the normalizer.
- `tests/eval/test_metrics.py` — NEW `TestNormalizeSourceSpan` (7 tests: None/empty/whitespace/sentinel/padded/passthrough/near-miss).
- `docs/progress/STEP_009_*` (this file) + `PROGRESS.md` index update.
- NOT changed: `data/eval/qa_pairs.jsonl` (frozen), `results/experiments.csv` row 3 (computed under v1 logic — immutable), `results/leaderboard.json` (no new full run).
- NOT committed: `results/smoke/exp_009_oos_fix_check_*/` (ephemeral proof), `data/eval/qa_pairs.limit6.jsonl` (regenerable slice).

### 3. How it works
OOS Q's now normalize to `""` before scoring, so the pre-existing branches
behave as STEP_006 designed: OOS content-hit = True (vacuous — no source to
miss), OOS content-cite = `"I cannot" in answer`. Non-OOS spans are unaffected
(never equal the sentinel — the generator emits it only for OOS). Near-miss
strings (e.g. `"<no relevantSpan>"`) deliberately do NOT normalize, so a
typo'd real span can't silently vanish.

### 4. How to verify
```bash
uv run pytest tests/eval/test_metrics.py tests/eval/test_ragas_runner.py tests/test_chunking.py -q
$env:CHUNKER_STRATEGY='semantic'; uv run python -m finrag.cli.eval --exp exp_009_oos_fix_check --limit 6 --smoke
# q_0006 (OOS) row must show source_span '' with hit_at_5_content true (was false)
```

### 5. Result / numbers
- Unit: 60 passed (7 new). Ruff: no new issues (one self-introduced `__all__` sort fixed; rest pre-existing).
- Smoke 2026-09-07 (6 Q, AAPL, semantic, $0.0012): q_0006 OOS flipped False→True end-to-end; non-OOS rows byte-identical in behavior (spans verbatim). Aggregate smoke hit@5_content 0.833.
- Deterministic projection for exp_003 under fixed logic (no model calls involved in the flip): non-OOS content-hits stay 78/121, OOS 0→18/18, so overall hit@5_content would read (78+18)/139 = **0.6906** instead of 0.5612. Frozen row 3 keeps 0.5612 (immutable — recompute, don't rewrite); exp_004+ rows will be directly comparable only among themselves on OOS handling. Non-OOS 0.645 unchanged and comparable throughout.

### 6. How to recall
- STEP file: `docs/progress/STEP_009_oos_sentinel_fix.md`
- Code: `finrag/eval/metrics.py::normalize_source_span`, `::OOS_SPAN_SENTINEL`; `ragas_runner.py` read-time call
- Sentinel origin: `tests/eval/generate_qa_pairs.py:188-189`; stale-claim fix in its `_span_appears_in_chunk` docstring
- Proof: `results/smoke/exp_009_oos_fix_check_20260907_033807/per_question.jsonl` (q_0006 row)

### 7. Next step (STEP_010 candidate)
exp_004 structural chunker (section-aware budgets, P99): first full run scored end-to-end under fixed OOS logic. Optional: exp_003 re-run under fixed logic for a like-for-like content number (~2h, ~$0.06) — only if the 0.5612-vs-future comparison becomes confusing; the 0.6906 projection above likely suffices.
