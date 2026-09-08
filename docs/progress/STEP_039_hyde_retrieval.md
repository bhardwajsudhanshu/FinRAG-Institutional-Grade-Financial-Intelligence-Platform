# STEP_039 — HyDE hypothetical-doc retrieval + exp_044 scaffold

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** Last retrieval family with zero data gets an implementation; exp_044 isolates it vs exp_001. No ledger change.
- **Roadmap phase:** Retrieval leftovers (HyDE — the final untested family)

### 1. Why
All gains so far are document-side, ranking-side, or expansion-side.
HyDE attacks from the opposite end: instead of rephrasing the question
(multi-query) or matching it lexically (BM25), write the ANSWER's
hypothetical document and retrieve by doc-to-doc similarity. Last family
with no data; one variable vs exp_001 decides it.
(No new ADR: orthogonal-flag design follows the multiquery precedent;
stack-level decisions unchanged.)

### 2. What changed (files — this commit)
- `finrag/hyde.py` — NEW `HyDEGenerator` (Flash 10-K-register prose, temp 0.5, failure → "" never raises; injectable `generate_fn`) + `hyde_fuse()` (fuse precomputed base + hyde-side rankings) + `hyde_retrieve()` (thin wrapper, direct base). Both sides run the SAME dispatcher — composes with every strategy, zero special cases.
- `finrag/config.py` — `hyde_enabled=False`.
- `finrag/eval/ragas_runner.py` — expander-style once-per-run construction; per-Q write→fuse chain inside the try (base = multiquery-aware); per-Q `hyde` field.
- `finrag/cli/eval.py` — prints `HyDE:` line.
- `tests/test_hyde.py` — NEW, 9 tests (writer hygiene, anchored fusion, empty fallback, determinism, factories).
- `docs/experiments/exp_044_hyde/{README,config.yaml,analysis.md}` — NEW scaffold (one-variable-vs-exp_001 design).
- `docs/progress/STEP_039_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (12 rows), leaderboard, eval set, all strategies.
- NOT committed: `results/smoke/exp_044_hyde_*/` (ephemeral).

### 3. How it works
`hyde_enabled` on: per Q, Flash writes a 3–6 sentence hypothetical 10-K
excerpt → `hyde_fuse` RRF-fuses [base ranking, hyde-doc ranking] → top-5
→ rerank chain unchanged. Off: zero extra calls. With multiquery also on:
expansion first, then one HyDE doc (not per paraphrase — cost discipline).

### 4. How to verify
```bash
uv run pytest tests/test_hyde.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=dense HYDE_ENABLED=true VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_044_hyde --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 9 passed. During-step correction, recorded: first `hyde_retrieve` draft special-cased hybrid-parent remapping with dead lines (same disease as STEP_034's first multiquery draft, same cure — fuse final rankings, delete the special cases).
- Ruff: own F401s fixed (redundant imports after the simplification); rest pre-existing.
- Smoke 2026-09-08 (6 Q, AAPL naive 97, $0.0017): content **1.000 (6/6, fifth ever — q_0005 True)**, cr=1.0/fa=0.85 (lowest smoke faithfulness yet — one wobble), ~17s/Q. AAPL slice officially saturated: five straight perfect smokes across five mechanisms.

### 6. How to recall
- STEP file: `docs/progress/STEP_039_hyde_retrieval.md`
- Code: `finrag/hyde.py`; tests: `tests/test_hyde.py`
- Exp: `docs/experiments/exp_044_hyde/`
- Proof: `results/smoke/exp_044_hyde_20260908_152535/` (untracked)

### 7. Next step (STEP_040)
Full exp_044 run (~50 min + 139 HyDE calls) → vague-Q concentration verdict vs exp_001 (0.6043) + all-in cost note → leaderboard. If HyDE wins, hybrid+HyDE follow-up; if noise, question-side work closes with multiquery.
