# STEP_024 — MiniLM cross-encoder challenger + exp_031 scaffold

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Cheap-rerank challenger implemented, tested, smoke-verified. No ledger change.
- **Roadmap phase:** Rerank (challenger live; decides whether the sweep gets affordable)

### 1. Why
exp_030 won quality at $0.171/42s-per-Q — undeployable per-query and
un-nightly-able. ADR-006 named MiniLM the challenger: match Flash's
ordering at $0 scoring and ~1s CPU per 10. (No new ADR — ADR-006 already
frames this exact comparison.)

### 2. What changed (files — this commit)
- `pyproject.toml` (`eval` extra) + `uv.lock` — NEW `sentence-transformers==6.0.1` (+ torch 2.14.0 CPU ~118MB, transformers, scikit-learn, sympy...). Install was uneventful — the feared Windows torch pain did not materialize.
- `finrag/rerank.py` — NEW `CrossEncoderReranker` (lazy model load, one batched `predict`, 2000-char truncation, failure → retrieval order) + `DEFAULT_CROSS_ENCODER_MODEL` + factory branch. Same reorder-only contract and deterministic tie-breaks as Flash.
- `finrag/config.py` — `rerank_backend` comment gains `cross-encoder`.
- `tests/test_rerank.py` — 4 new tests (ordering, failure-order, truncation count, live-MiniLM path with skip-if-unavailable).
- `docs/experiments/exp_031_minilm_rerank/{README,config.yaml,analysis.md}` — NEW scaffold (cost/latency-challenger framing, full command with `HF_HOME` + all pins).
- `docs/progress/STEP_024_*` (this file) + `PROGRESS.md` index update.
- Env (not a file change): model cached at `F:/.hf-cache` (~90MB, one-time download); `HF_HOME` must prefix MiniLM runs to honor the F:-drive discipline (README + analysis record the full command).
- NOT changed: ledger (8 rows), leaderboard, eval set, Flash path.
- NOT committed: `results/smoke/exp_031_minilm_rerank_*/` (ephemeral).

### 3. How it works
`CrossEncoderReranker().rerank(q, items, top_k)`: single `predict([(q, t)...])` → same sort contract as Flash (score desc, retrieval desc, rank asc) → truncate. `score_fn` injectable (offline tests); real path truncates texts to 2000 chars (512-token cap).

### 4. How to verify
```bash
$env:HF_HOME='F:/.hf-cache'; uv run pytest tests/test_rerank.py -q
$env:HF_HOME='F:/.hf-cache'; $env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='hybrid'; $env:RERANK_BACKEND='cross-encoder'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_031_minilm_rerank --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 16 passed in test_rerank (4 new; live-MiniLM path ran, not skipped — cache present). Ruff: only pre-existing classes.
- During-step correction, recorded: first draft let injected-`score_fn` exceptions propagate while model failures sank — inconsistent; both now sink (same contract as Flash).
- Shell note (own mistake, recorded): PowerShell has no `<<EOF` heredocs and no `tail` — use edit/write tools and `Select-Object`, never shell redirection/pipes-to-Unix.
- Smoke 2026-09-07 (6 Q, AAPL naive 97, $0 scoring): content 0.833 (5/6, same as Flash smoke incl. same only-miss), cr/fa 1.0, 160s wall (~2× faster than Flash smoke already at n=6).

### 6. How to recall
- STEP file: `docs/progress/STEP_024_minilm_challenger.md`
- Code: `finrag/rerank.py::CrossEncoderReranker`; tests: `tests/test_rerank.py::TestCrossEncoder`
- Exp: `docs/experiments/exp_031_minilm_rerank/`
- Proof: `results/smoke/exp_031_minilm_rerank_20260907_194343/` (untracked)

### 7. Next step (STEP_025)
Full exp_031 run (~50 min — no per-pair LLM calls, so Flash's 2h collapses) → quality-within-noise verdict vs exp_030 (content 0.8849 / cite 0.7266) + latency ledger + $0-scoring confirmation → leaderboard.
