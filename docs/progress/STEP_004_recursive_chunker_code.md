# STEP_004 — Recursive chunker code (exp_002 scaffold)

- **Date:** 2026-09-05
- **Git commit:** `3b4f77a` Recursive chunking is implemented
- **Goal:** Second chunker plugged in without touching retrieve/generate/eval.
- **Roadmap phase:** Week 3-4 Chunking (1/5)

### 1. Why
Naive 512-token windows split mid-paragraph. Recursive (paragraph → line → sentence → word → char) is the cheapest structure-aware upgrade; tests if bad hit@5 is a boundary problem.

### 2. What changed
- `finrag/chunking.py:116-277` — `recursive_chunk_text` (2000 chars/200 overlap ≈ 500/50 tokens) + `chunk_sections_recursive` + `CHUNKER_DISPATCH` + `chunk_sections_by_strategy`.
- `finrag/config.py:54` — `chunker_strategy: naive | recursive | semantic | structural | late | contextual` (only first two wired; rest are placeholders).
- `finrag/cli/eval.py`, `finrag/eval/ragas_runner.py` — use `settings.chunker_strategy` dispatch.
- `docs/experiments/exp_002_recursive/{README,config.yaml}` — hypothesis + frozen params.
- `tests/test_chunking.py` — NEW: naive + recursive unit tests.
- `tests/eval/test_leaderboard.py`, `update_leaderboard.py` — leaderboard hardening.

### 3. How it works
- Separators `["\n\n", "\n", ". ", " ", ""]` tried longest-first; oversized pieces recurse with next separator.
- Same chunk_id shape, but `metadata.chunker="recursive"` so post-hoc filtering works.
- Run: `CHUNKER_STRATEGY=recursive uv run python -m finrag.cli.eval --exp exp_002_recursive`.

### 4. How to verify
```bash
make test   # chunking tests
CHUNKER_STRATEGY=recursive make eval-smoke
```

### 5. Result
Code wired; full run deferred to STEP_005. Smoke proved `n_chunks` jumps (denser index) — foreshadowed the metric artifact.

### 6. How to recall
- Commit: `git show 3b4f77a --stat`
- Code: `finrag/chunking.py:137-277`
- Exp scaffold: `docs/experiments/exp_002_recursive/README.md`, `config.yaml`

### 7. Next step
STEP_005 runs exp_002 fully and discovers the chunk_id-based hit@5 is brittle across chunkers.
