# STEP_012 — Phase 3 opens: ADR-004 + BM25/hybrid retrieval paths

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Retrieval becomes a first-class experiment axis (ADR-004); BM25 baseline + hybrid RRF implemented, tested, smoke-verified. No ledger change.
- **Roadmap phase:** Week 5-6 Vector DBs / Week 7-8 Retrieval (opens; chunking 4/5 scored, exp_005 deferred)

### 1. Why
STEP_011 verdict: no chunker beats naive on context_recall; next gains must
come retrieval-side (exp_001 per-ticker analysis: dense misses numbers/names
in narrative filings). ADR-004 (written first, per locked rule) fixes the
order: BM25 ablation (exp_020) → hybrid RRF (exp_021), naive chunks fixed,
in-memory only (vector-DB phase stays separate).

### 2. What changed (files — this commit)
- `docs/decisions/adr_004_retrieval_direction.md` — NEW (decision, RRF rationale k=60, exp_020/021 plan, alternatives).
- `finrag/retrieval.py` — NEW `tokenize_for_bm25` (regex, no NLTK data), `BM25Index` (lazy rank_bm25 import, `__len__`, empty/top_k<=0 → []), `build_bm25_index`, `reciprocal_rank_fusion` (0-based ranks, k=60), `retrieve_with_strategy` (dense/bm25/hybrid dispatcher, loud ValueError). Dense path byte-untouched.
- `finrag/config.py` — NEW `retrieval_strategy="dense"` (+ env `RETRIEVAL_STRATEGY`).
- `finrag/eval/ragas_runner.py` — `build_index_for_qa_pairs(..., strategy=None)` builds ONLY needed indexes (pure-BM25 embeds nothing); returns bundle `{strategy, dense, bm25, chunks_by_id, n_chunks}`; per-Q uses dispatcher; per-Q record gains `retrieval_strategy`; `n_chunks` from bundle. Import re-sorted (self-nit).
- `finrag/cli/eval.py` — prints `Retrieval:` line (recall).
- `tests/test_retrieval.py` — NEW, 13 tests (tokenizer, BM25 exact-match number/name, empties, RRF order/math, dispatcher incl. bm25-without-dense + unknown-reject).
- `docs/experiments/exp_020_bm25/{README,config.yaml,analysis.md}` — NEW scaffold (naive chunks = exp_001 isolation).
- `docs/progress/STEP_012_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (4 rows), leaderboard, eval set, dense behavior.
- NOT committed: `results/smoke/exp_020_bm25_*/` (ephemeral).

### 3. How it works (bit-by-bit)
- RRF: `score(d) = Σ 1/(60 + rank + 1)` over the two top-20 lists → top-5; chunk objects via `bundle["chunks_by_id"]`, missing IDs skipped (can't happen — both lists come from the same chunk set — but loud-crash avoidance is deliberate).
- Hybrid still embeds (dense side) — only pure-BM25 skips embedding entirely.
- `ask.py` untouched (dense-only smoke CLI; retrieval axis lives in the eval runner).

### 4. How to verify
```bash
uv run pytest tests/test_retrieval.py tests/test_chunking.py tests/eval/test_metrics.py tests/eval/test_ragas_runner.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=bm25 uv run python -m finrag.cli.eval --exp exp_020_bm25 --limit 6 --smoke
# per-Q rows must carry retrieval_strategy=bm25; index build ~1s
```

### 5. Result / numbers
- Unit: 79 passed (13 new). Ruff: no new issues (own import re-sorted; rest pre-existing).
- Smoke 2026-09-07 (6 Q, AAPL naive 97 chunks, $0.0016): content 0.833 = chunk_id 0.833 (agree — naive IDs valid); **index 0.9s**; only miss q_0005 (same as structural). Full-run ETA ~30 min (no chunk-embed phase).
- No performance claims yet — 6 Q proves plumbing, not quality.

### 6. How to recall
- STEP file: `docs/progress/STEP_012_phase3_bm25_hybrid.md`
- Decision: `docs/decisions/adr_004_retrieval_direction.md`
- Code: `finrag/retrieval.py` (BM25/RRF block), `config.py::retrieval_strategy`, runner bundle
- Tests: `tests/test_retrieval.py`
- Exp: `docs/experiments/exp_020_bm25/`
- Proof: `results/smoke/exp_020_bm25_20260907_050101/` (untracked)

### 7. Next step (STEP_013)
Full exp_020 BM25 run (`CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=bm25`, ~30 min) → analysis (lookup-vs-section split = ADR-004 bet; WMT/AMZN check) → leaderboard. Then scaffold + run exp_021 hybrid.
