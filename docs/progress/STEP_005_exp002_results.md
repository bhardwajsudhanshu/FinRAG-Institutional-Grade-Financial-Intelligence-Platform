# STEP_005 — exp_002 full run + analysis (the metric artifact)

- **Date:** 2026-09-05 09:07 UTC (51 min wall, 3057s pipeline)
- **Git commit:** `84a88f5` recursive results
- **Goal:** Score recursive vs naive on the frozen 139-Q set.
- **Roadmap phase:** Week 3-4 Chunking

### 1. Why
First cross-chunker comparison. Expected +5-10pp hit@5 from paragraph respect.

### 2. What changed
- `docs/experiments/exp_002_recursive/analysis.md` — full root-cause writeup (the most important doc in the repo right now).
- `results/experiments.csv` row 2 (immutable), `results/exp_002_recursive/per_question.jsonl` (139 rows).
- `results/leaderboard.json` + `leaderboard_snapshots/leaderboard_20260905_090705.json` refreshed (exp_001 still leads).

### 3. What happened (numbers)
Locked: context_recall 0.8058→0.7913 (-1.4pp), faithfulness 0.8847→0.8595 (-2.5pp), answer_relevancy 0.7428→0.7080 (-3.5pp), hit@5 0.604→0.324 (-28pp), cite_acc 0.561→0.216 (-34pp), chunks 4447→5412 (+21.7%), latency +14.2%, cost -21.5%.
Root cause: eval `source_chunk_id` was minted under naive boundaries. Under recursive, same paragraph = different ID → chunk_id hit can never fire (only 33/139 IDs still exist). RAGAS (content-judged) barely moved — proof it's a measurement artifact, not a chunker failure.
Content-based recompute (same ticker+section in top-5): 0.734→0.741 (+0.7pp); section Q +4.4pp, synthesis +11.1pp.

### 4. How to verify
```bash
# locked rows
cat results/experiments.csv
# per-Q audit
ls results/exp_002_recursive/per_question.jsonl
```

### 5. Decisions locked
1. Need content-anchored `hit@5_content` / `cite_acc_content` (source_span substring, not chunk_id) before exp_003.
2. Recursive ≈ naive overall, helps section/synthesis; produces too many small chunks on narrative filings.
3. Never rewrite frozen rows — keep artifact + caveat.

### 6. How to recall
- Commit: `git show 84a88f5 --stat`
- Analysis: `docs/experiments/exp_002_recursive/analysis.md` (read fully before any chunker work)
- Ledger: `results/experiments.csv` line 3, `results/leaderboard.json`

### 7. Next step
STEP_006 implements the content-anchored fix so exp_003+ scores are trustworthy.
