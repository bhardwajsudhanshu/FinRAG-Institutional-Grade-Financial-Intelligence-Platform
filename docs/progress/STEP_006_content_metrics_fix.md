# STEP_006 — Content-anchored metrics fix (PENDING commit)

- **Date:** 2026-09-06 (uncommitted as of this STEP file)
- **Git commit:** PENDING — `git status` shows 15 changed/new files (see §2)
- **Goal:** Make hit@5 / citation_accuracy trustworthy across chunker changes.
- **Roadmap phase:** Week 3-4 Chunking (unblocks exp_003 semantic)

### 1. Why
STEP_005 proved chunk_id-based hit@5 conflates "right context retrieved?" with "does the old chunk_id still exist?". Fix without editing frozen eval set: use `source_span` substring matching instead.

### 2. What changed (uncommitted — commit this next)
- `finrag/eval/metrics.py` — NEW (96 lines): `span_appears_in_chunk` (normalize whitespace+lowercase; full-span contains, else head/tail 100-char probes for straddled paragraphs).
- `finrag/eval/ragas_runner.py` — computes `hit_at_5_content` + `citation_accuracy_content` per Q, writes them into `per_question.jsonl`, returns them in `ExperimentResult`.
- `finrag/eval/__init__.py` — exports `span_appears_in_chunk`.
- `finrag/cli/eval.py` — `EXPERIMENTS_CSV_FIELDS` += 2 columns; `--smoke` mode routes to `results/smoke/<exp>_<ts>/` (never pollutes canonical CSV/leaderboard).
- `tests/eval/update_leaderboard.py` — new `chunking_content` category (`hit_at_5_content`, winner=null until exp_003 lands).
- `tests/eval/test_metrics.py` — NEW (181 lines): direct/head/tail/empty/OOS/realistic-10K cases.
- `tests/eval/test_ragas_runner.py` — content-field default-None (exp_001/002 compat) + populated (exp_003+) tests.
- `tests/eval/test_leaderboard.py`, `generate_qa_pairs.py` — share canonical matcher, leaderboard compat.
- `results/smoke/exp_003_smoke_metric_test_20260906_054221/` — proof smoke run (5 Q) with new columns populated.
- Deleted: `.claude/scheduled_tasks.lock` (stale).

### 3. How it works
- `finrag/eval/metrics.py:56-96` — `_normalize` collapses `\s+`→space + lowercase; empty span/chunk → False (OOS has empty span by design → counted as hit only if model says "I cannot").
- Runner `ragas_runner.py:288-342` — per Q: content hit = any top-5 chunk text contains span; content cite = any cited chunk text contains span (via `chunk_id_to_text` lookup).
- CSV schema now 14 cols (was 12); old rows have empty content cols (None) — backward compatible.

### 4. How to verify
```bash
uv run pytest tests/eval/test_metrics.py tests/eval/test_ragas_runner.py -v
uv run python -m finrag.cli.eval --exp exp_003_smoke_metric_test --limit 5 --smoke
# check results/smoke/<exp>_<ts>/smoke_experiments.csv has hit_at_5_content populated
```

### 5. Result
Smoke passes (see `results/smoke/exp_003_smoke_metric_test_20260906_054221/smoke_experiments.csv`). Canonical `results/experiments.csv` untouched (still 2 rows) — correct, smoke never writes there.

### 6. How to recall
- Diff: `git diff HEAD --stat`, `git status --short`
- Code: `finrag/eval/metrics.py`, `finrag/eval/ragas_runner.py:62-89,288-342`
- Tests: `tests/eval/test_metrics.py`

### 7. Next step (STEP_007)
1. `git add finrag/eval/metrics.py finrag/eval/ragas_runner.py finrag/eval/__init__.py finrag/cli/eval.py tests/eval/ scripts/` + commit "content-anchored metrics (hit_at_5_content)".
2. Do NOT commit `results/smoke/*` (ephemeral) — keep `.gitignore` clean.
3. Then start exp_003 semantic: implement `chunk_sections_semantic` in `finrag/chunking.py`, add to `CHUNKER_DISPATCH`, create `docs/experiments/exp_003_semantic/{README,config.yaml}`, run full eval, write `analysis.md`, `make leaderboard`.
