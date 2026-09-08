# STEP_030 — Parent-doc retrieval + exp_041 scaffold (smoke 6/6)

- **Date:** 2026-09-08
- **Git commit:** PENDING (this step)
- **Goal:** Hierarchy becomes a retrieval axis; exp_041 isolates it against byte-identical parents. No ledger change.
- **Roadmap phase:** Retrieval leftovers (synthesis still trails — this is the structural answer)
- **Naming:** this STEP_030 is the progress step; exp_030_flash_rerank is the experiment. Step numbers and experiment numbers are independent sequences (PROGRESS.md rule).

### 1. Why
Synthesis Q's need coverage (multi-paragraph answers), lookup Q's need
precision — one chunk size can't serve both (chunking verdict). Parent-doc
splits the jobs: 256-token children retrieve, 512-token parents generate.
Parents byte-identical to exp_001 makes this a pure hierarchy ablation.
(No new ADR: ADR-004's retrieval-direction framing covers it; stack-level
decisions unchanged.)

### 2. What changed (files — this commit)
- `finrag/parentdoc.py` — NEW `build_parent_child_chunks()` (parents via naive chunker verbatim; children re-windowed 256/25, ids `{parent}:c{ii}`, `parent_id` metadata).
- `finrag/config.py` — `retrieval_strategy` gains `parent-doc` + `parentdoc_child_size/overlap` (256/25).
- `finrag/retrieval.py` — `retrieve_with_strategy` gains `parent-doc` branch (top-20 children → unique parents, best-child score, top-5); error lists 4 strategies.
- `finrag/eval/ragas_runner.py` — strategy resolved before chunking loop; parent-doc branch builds parents+children (naive pinned with loud warning otherwise), embeds CHILDREN into the dense slot, `chunks_by_id` = parents, `n_chunks` = parents (comparable), `n_child_chunks` in bundle.
- `tests/test_parentdoc.py` — NEW, 8 tests (parent identity, child shape/mapping, single-child, skips, validation, dispatch hit/dedup/top_k).
- `docs/experiments/exp_041_parent_doc/{README,config.yaml,analysis.md}` — NEW scaffold (numbered 041: 040 stays reserved for RAPTOR, indexing-family neighbor).
- `docs/progress/STEP_030_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (9 rows), leaderboard, eval set, dense/BM25/hybrid paths.
- NOT committed: `results/smoke/exp_041_parent_doc_*/` (ephemeral).

### 3. How it works
`build_index_for_qa_pairs(..., strategy="parent-doc")`: per filing, parents+children; child vectors embedded; `bundle["dense"]` = child index, `chunks_by_id` = parents. Per Q: 20 children → parents → top-5 → generate. Rerank composes unchanged on top (fetch widens, rerank orders parents).

### 4. How to verify
```bash
uv run pytest tests/test_parentdoc.py tests/test_retrieval.py -q
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=parent-doc VECTORDB_BACKEND=in-memory uv run python -m finrag.cli.eval --exp exp_041_parent_doc --limit 6 --smoke
```

### 5. Result / numbers
- Unit: 8 new pass; full fast suite green; ruff only pre-existing classes (one self-removed unused-noqa).
- During-step catches, recorded: (a) near-clobbered hybrid's return with the parent-doc edit — caught by immediate re-read, restored, verified (`git diff` review habit for shared-dispatch edits); (b) dropped my own dead params/imports before they fossilized (parent_size passthrough, private cross-module imports → `naive_chunk_text` reuse).
- Smoke 2026-09-08 (6 Q, AAPL 97 parents/280 children, $0.0017): content **1.000 (6/6, first ever — incl. q_0005, missed by ALL prior configs)**, cr/fa 1.0. Small-n euphoria warning stands — full run decides.

### 6. How to recall
- STEP file: `docs/progress/STEP_030_parent_doc_retrieval.md`
- Code: `finrag/parentdoc.py`; dispatch: `finrag/retrieval.py` parent-doc branch; runner: `ragas_runner.py` parent-doc branch
- Tests: `tests/test_parentdoc.py`
- Exp: `docs/experiments/exp_041_parent_doc/`
- Proof: `results/smoke/exp_041_parent_doc_20260908_072550/` (untracked)

### 7. Next step (STEP_031)
Full exp_041 run (~60 min — ~2× embedding units, children cost) → section/synthesis-vs-lookup split verdict vs exp_001 → leaderboard. Bars: section/synthesis content above exp_001 (0.689/0.333 terms); lookup must not collapse.
