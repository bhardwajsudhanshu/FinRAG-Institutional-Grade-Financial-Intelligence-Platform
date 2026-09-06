# STEP_003 — Eval set (139 Q v1) + exp_001 baseline

- **Date:** 2026-09-05
- **Git commit:** `6104e9b` tested and implemented 139 questions and evaluated the accuracy
- **Goal:** Frozen benchmark + first real numbers every later experiment must beat.
- **Roadmap phase:** Week 1-2 Foundation (done)

### 1. Why
Without a fixed Q set + fixed metrics, chunker/retriever comparisons are meaningless. ADR-003 locks schema.

### 2. What changed
- `tests/eval/generate_qa_pairs.py` — NEW: 2-pass Q-gen (pro generates, flash verifies + substring check). Drops failures, logs drop rate.
- `data/eval/qa_pairs.jsonl` — NEW: v1 frozen = 139 Q (not 200 — COST/MSFT/PFE ran out of citable spans; 139 > 100 minimum for hit@5 SE≈4%).
- `finrag/eval/__init__.py`, `ragas_runner.py` — NEW: `run_experiment` (build index → retrieve → generate → custom metrics → `ragas.evaluate`).
- `tests/eval/update_leaderboard.py` — NEW: rolling `leaderboard.json` + immutable `leaderboard_snapshots/`.
- `docs/decisions/adr_003_eval_methodology.md` — locks: 4 Q-types, 3 RAGAS + 3 custom metrics, CSV schema.
- `docs/experiments/SCHEMA.md` — documents `experiments.csv` + `per_question.jsonl` shape.
- `docs/experiments/exp_001_naive_baseline/{README,config.yaml,analysis.md}` — filled with real numbers.
- `results/experiments.csv` row 1, `results/exp_001_naive_baseline/per_question.jsonl` (139 rows).
- `scripts/patch_langchain_vertexai_shim.py` — fixes ragas 0.4.3 `chat_models.vertexai` import.

### 3. How it works (bit-by-bit)
- Q-types: lookup 67 (48%), section 45 (32%), OOS 18 (13%), synthesis 9 (6%). Each has `source_chunk_id` + `source_span` (≤600 chars) + `ground_truth_answer`.
- Runner (`finrag/eval/ragas_runner.py:193-425`): for each Q → `retrieve(top_k=5)` → `generate` → chunk_id hit@5/cite_acc → RAGAS (OOS excluded from RAGAS, counted inverse in hit@5).
- Leaderboard categories: chunking/retrieval = context_recall, end_to_end = faithfulness.

### 4. How to verify
```bash
make eval-smoke   # 5 Q fast path
make eval         # full 139 Q (~45 min Vertex)
make leaderboard
```

### 5. Result (frozen row 1)
n=139, filings=20, chunks=4447, context_recall=0.8058, faithfulness=0.8847, answer_relevancy=0.7428, hit@5=0.6043, cite_acc=0.5612, latency 8731ms, $0.038. Weak spots: synthesis hit@5=0.333, WMT/AMZN/PFE/GS/NVDA worst tickers.

### 6. How to recall
- Commit: `git show 6104e9b --stat`
- ADR: `docs/decisions/adr_003_eval_methodology.md`
- Exp: `docs/experiments/exp_001_naive_baseline/`
- Data: `data/eval/qa_pairs.jsonl`, `results/exp_001_naive_baseline/per_question.jsonl`

### 7. Next step
STEP_004 adds the recursive chunker so exp_002 can run on the same frozen set.
