# STEP_007 — Semantic chunker + exp_003 scaffold (smoke-verified)

- **Date:** 2026-09-06
- **Git commit:** PENDING (this step only — STEP_006 was closed by `9261360` during this step, see note below)
- **Goal:** Third chunker live behind dispatch, exp_003 scaffolded, smoke proves content metrics work on a new chunker.
- **Roadmap phase:** Week 3-4 Chunking (2/5 — full 139-Q run deferred to STEP_008)

### 1. Why
STEP_005 showed recursive ≈ naive once the chunk_id artifact is removed, with
section/synthesis hints (+4.4pp / +11.1pp content-based). Semantic (meaning,
not punctuation) is the next cheapest structural bet, and the first consumer
of the STEP_006 `hit_at_5_content` columns.

### 2. What changed (files)
- `finrag/chunking.py` — NEW `semantic_chunk_text` + `chunk_sections_semantic` + `CHUNKER_DISPATCH["semantic"]` (~130 lines). Imports `math`, `re`. `chunk_sections_semantic` accepts `embed_fn` for offline tests.
- `tests/test_chunking.py` — 7 new tests (empty/single/split-at-topic/max-tokens/invalid-args/metadata/dispatch) with deterministic `_fake_embed_fn` (finance vs sports 2-D vectors).
- `docs/experiments/exp_003_semantic/{README,config.yaml,analysis.md}` — NEW scaffold (hypothesis, frozen P95/512/50 params, smoke filled, full-run TODO).
- `docs/progress/STEP_007_*` (this file) + `PROGRESS.md` index update.
- Already closed by `9261360 updated logs` (committed mid-step by the user):
  `finrag/eval/metrics.py`, `ragas_runner.py`, `__init__.py`, `cli/eval.py`,
  `tests/eval/*`, `update_leaderboard.py`, `results/leaderboard.json` +
  snapshot, `docs/progress/STEP_001-006` + template + `PROGRESS.md` v1.
  Note: `9261360` also swept in two small smoke files
  (`results/smoke/exp_003_smoke_metric_test_*/...`) that predate the locked
  smoke-ephemeral rule below — left as-is (history is append-only); from
  this step on, smoke stays untracked.
- NOT committed (ephemeral): `results/smoke/exp_003_semantic_20260906_211228/*`, older `results/smoke/exp_003_smoke_metric_test_*`, `data/eval/qa_pairs.limit5.jsonl` (regenerable smoke slice).

### 3. How it works (bit-by-bit)
- `chunking.py::_split_sentences` — regex `(?<=[.!?])\s+` + blank lines.
- `semantic_chunk_text(text, max_tokens=512, overlap=50, P=95, embed_fn=None)`:
  1. sentences → `embed_fn` or `get_embedder().embed_batch` (lazy import keeps chunking import-light);
  2. consecutive `_cosine_distance` → `_percentile(dist, 95)` threshold → breakpoints;
  3. greedy pack to 512 tokens, cutting early at breakpoints; 1-sentence overlap carried forward; monster sentences fall back to `naive_chunk_text`.
- `chunk_sections_semantic(...)` — same chunk_id shape, `metadata.chunker="semantic"` + `semantic_threshold_p`.
- Dispatch: `CHUNKER_STRATEGY=semantic` selects it (`chunk_sections_by_strategy`, loud KeyError otherwise).
- Cost note: chunking embeds sentences once + index embeds chunks once (~2× embed bill on Vertex; free on mock).

### 4. How to verify
```bash
uv run pytest tests/test_chunking.py tests/eval/test_metrics.py tests/eval/test_ragas_runner.py -q
$env:CHUNKER_STRATEGY='semantic'; uv run python -m finrag.cli.eval --exp exp_003_semantic --limit 5 --smoke
# check results/smoke/exp_003_semantic_<ts>/smoke_experiments.csv has hit_at_5_content populated
```

### 5. Result / numbers
- Unit: 53 passed (`test_chunking` + `test_metrics` + `test_ragas_runner`).
- Smoke 2026-09-06 (5 Q, AAPL 2025-10-31, Vertex): 141 chunks, cr=1.0, fa=1.0, ar=0.7669, hit@5=0.40 vs **hit@5_content=0.80**, cite 0.40 vs 0.80, 5073ms/Q, $0.0010. Gap reproduces exp_002 artifact → fix validated on new chunker. Index build 139s (sentence embed cost — full run est. 45-60 min, $0.05-0.08).
- Canonical `results/experiments.csv` untouched (2 rows) — correct, smoke never writes there.

### 6. How to recall
- STEP file: `docs/progress/STEP_007_semantic_chunker_scaffold.md`
- Code: `finrag/chunking.py::semantic_chunk_text`, `::chunk_sections_semantic`, `::CHUNKER_DISPATCH`
- Tests: `tests/test_chunking.py` (semantic block)
- Exp: `docs/experiments/exp_003_semantic/`
- Smoke: `results/smoke/exp_003_semantic_20260906_211228/smoke_experiments.csv`
- Index: `docs/progress/PROGRESS.md`

### 7. Next step (STEP_008)
1. Commit this step only (explicit pathspec — command in PROGRESS.md; smoke stays untracked).
2. Full run: `CHUNKER_STRATEGY=semantic uv run python -m finrag.cli.eval --exp exp_003_semantic` (~50 min) → fill `analysis.md` per-type/ticker tables → `make leaderboard` → new snapshot.
3. Decision: does semantic beat recursive on `hit_at_5_content`? If yes, chunking track leader changes; if no, proceed to exp_004 structural.
