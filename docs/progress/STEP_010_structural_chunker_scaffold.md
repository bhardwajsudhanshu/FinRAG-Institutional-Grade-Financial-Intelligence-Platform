# STEP_010 — Structural chunker + exp_004 scaffold (smoke-verified)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Fourth chunker live behind dispatch; exp_004 scaffolded; smoke proves budgets + fixed OOS logic work together.
- **Roadmap phase:** Week 3-4 Chunking (3/5 — full 139-Q run deferred to STEP_011)

### 1. Why
exp_003 taught: semantic coherence helps faithfulness (0.8932) but P95
over-fragments (6858 chunks, +54%) and needs 64-min sentence-embedding.
The exp_003 decision (analysis.md) pointed at section-aware budgets:
10-K sections have known discourse shapes (ADR-001), so Risk lists want
small chunks, MD&A/financials want wide ones. Structural bets document
structure is the cheaper signal — same paragraph-aware splitter as
exp_002, only budgets vary, zero chunk-time embedding.

### 2. What changed (files — this commit)
- `finrag/chunking.py` — NEW `SECTION_CHUNK_BUDGETS` (1a/1b/1c→1200/200; 1/2/3/7a→2000/200; 7/8→3000/200; unknown→2000/200 fallback) + `chunk_sections_structural()` (reuses `recursive_chunk_text`; metadata `chunker="structural"` + `section_budget`) + `CHUNKER_DISPATCH["structural"]`.
- `tests/test_chunking.py` — 6 new tests (budget table coverage/validity, risk<MDA hypothesis, metadata, per-section application on identical text, unknown-section fallback, dispatch).
- `docs/experiments/exp_004_structural/{README,config.yaml,analysis.md}` — NEW scaffold (hypothesis, frozen budgets, smoke filled, full-run TODO).
- `docs/progress/STEP_010_*` (this file) + `PROGRESS.md` index update.
- NOT changed: canonical ledger (still 3 rows), leaderboard, eval set.
- NOT committed: `results/smoke/exp_004_structural_*/` (ephemeral), `data/eval/qa_pairs.limit6.jsonl` (regenerable).

### 3. How it works (bit-by-bit)
- Budgets are (chars, overlap) pairs in LangChain convention, matching recursive's 2000/200 default so exp_002 is the fair baseline; only 1a/1b/1c (1200) and 7/8 (3000) deviate.
- `chunk_sections_structural(..., budgets=None)` accepts an override table (testable, future-tunable without code change); `chunk_sections_by_strategy` forwards kwargs, so `CHUNKER_STRATEGY=structural` just works.
- Unknown `section_id` → default budget (loud KeyError only for unknown *strategy*, never for new sections).

### 4. How to verify
```bash
uv run pytest tests/test_chunking.py -q
$env:CHUNKER_STRATEGY='structural'; uv run python -m finrag.cli.eval --exp exp_004_structural --limit 6 --smoke
# per-Q must show chunker=structural behavior + q_0006 OOS content True
```

### 5. Result / numbers
- Unit: 29 passed (6 new). Ruff: no new issues (5 flags all pre-existing classes).
- Smoke 2026-09-07 (6 Q, AAPL, $0.0016): hit@5_content 0.833 (5/6, OOS True), cr=0.80, fa=1.00. **Index build 19.0s** vs semantic's 108.8s same filing — full run should index in ~10 min, total ~45 min.
- AAPL chunk count identical to semantic here (141) — coincidence of one filing; budgets diverge at scale (JPM/GS MD&A-heavy filings are the test).

### 6. How to recall
- STEP file: `docs/progress/STEP_010_structural_chunker_scaffold.md`
- Code: `finrag/chunking.py::SECTION_CHUNK_BUDGETS`, `::chunk_sections_structural`
- Tests: `tests/test_chunking.py` (structural block)
- Exp: `docs/experiments/exp_004_structural/`
- Proof: `results/smoke/exp_004_structural_20260907_034645/per_question.jsonl` (untracked)

### 7. Next step (STEP_011)
Full run: `CHUNKER_STRATEGY=structural uv run python -m finrag.cli.eval --exp exp_004_structural` (~45 min, no sentence-embedding phase) → analysis per-type/ticker + `make leaderboard`. Decision targets: context_recall > 0.8058, n_chunks in 4447–5412, `hit_at_5_content` as first clean new-era number alongside exp_003's 0.6906 projection.
