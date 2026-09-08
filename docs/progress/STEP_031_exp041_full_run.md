# STEP_031 — exp_041 full run (139 Q): hierarchy helps, hybrid still leads

- **Date:** 2026-09-08 (07:32–08:25 UTC, 3199.0s single attempt)
- **Git commit:** PENDING (this step)
- **Goal:** Section/synthesis-vs-lookup split verdict on hierarchy; update every record.
- **Roadmap phase:** Retrieval leftovers (parent-doc measured; multi-query/HyDE + hybrid-combo remain)
- **Naming:** this STEP_031 is the progress step; exp_031_minilm_rerank is the experiment. Independent sequences (PROGRESS.md rule).

### 1. Why
STEP_030 smoke went 6/6 (first ever) on the exact hypothesized mechanism.
Only a full run can say whether hierarchy scales or was small-n euphoria.

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 10 `exp_041_parent_doc` (clean append, 4447 parents).
- `results/exp_041_parent_doc/per_question.jsonl` — NEW, 139 rows (all parent-doc).
- `results/leaderboard.json` — refreshed, NO winner change (correct); snapshot `leaderboard_20260908_082522.json`.
- `docs/experiments/exp_041_parent_doc/analysis.md` — full analysis (half-right verdict, cost/point lesson, combo follow-up).
- `docs/progress/STEP_031_*` (this file) + `PROGRESS.md` index update.
- No code / schema / eval-set changes. NOT committed: `results/smoke/*` (user snapshots separately).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='naive'; $env:RETRIEVAL_STRATEGY='parent-doc'; $env:RERANK_BACKEND='none'; $env:VECTORDB_BACKEND='in-memory'; uv run python -m finrag.cli.eval --exp exp_041_parent_doc
uv run python tests/eval/update_leaderboard.py
```
(All four pinned — machine-OS chroma trap.) Index 658s (4447 parents + ~13.2K children embedded). No kill, no rerun, no 429s. STEP_014 fix fired live a second time (07:54 log) — no Q lost.

### 4. Result / numbers
139 Q / 4447 parents / ~13.2K children; cr=0.7397, fa=**0.9233 (best non-rerank)**, ar=0.6989; hit@5=0.5899, cite=0.5324; **content=0.6978 (+9.4pp vs naive — hierarchy is real)**, cite_content=0.6763; 10239ms/Q; $0.0375. Per-type: lookup 0.672 (held), section 0.644 (flat), synthesis 0.556 (+22pp vs exp_001 terms — mechanism confirmed, modest). Smoke 6/6 did NOT scale (0.698) — euphoria warning validated. Verdict vs hybrid 0.8129: loses by 11pp at 3× index cost — worst cost/point yet; useful, not leading.

### 5. Evaluation/methods changes
1. **Ledger**: clean row-10 append. No migration.
2. **Leaderboard**: refreshed, no winner change (exp_030 sweeps all 5). Snapshot added (by design).
3. **No methods changes.**

### 6. How to recall
- STEP file: `docs/progress/STEP_031_exp041_full_run.md`
- Row: `results/experiments.csv` line 11; per-Q: `results/exp_041_parent_doc/per_question.jsonl`
- Leaderboard: `results/leaderboard.json` + `leaderboard_20260908_082522.json`
- Exp: `docs/experiments/exp_041_parent_doc/analysis.md`

### 7. Next step (STEP_032 candidate)
Hybrid+parent-doc combo (children-BM25 + parent contexts — the cost/point redemption arc) or multi-query/HyDE (question-side, untested) or serving hardening. Recommend combo: single variable vs both parents (exp_041 and exp_021), reuses all existing code paths.
