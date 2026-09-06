# STEP_008 — exp_003 full run (139 Q) + ledger updates

- **Date:** 2026-09-06 → 2026-09-07 (22:55–00:40 UTC)
- **Git commit:** PENDING (this step)
- **Goal:** Score semantic on the frozen set; update every record the run changed: performance (CSV row), leaderboard, analysis, progress, methods notes.
- **Roadmap phase:** Week 3-4 Chunking (2/5 full runs done)

### 1. Why
STEP_007 smoke (5 Q) validated plumbing but proves nothing statistically.
The chunking track decision needs the full 139-Q row with content columns.

### 2. What changed (files — this commit)
- `results/experiments.csv` — row 3 `exp_003_semantic` (written by CLI) + **header migrated 12→14 cols** (appended `hit_at_5_content,citation_accuracy_content`; rows 1-2 padded `,,` = None/frozen, values untouched).
- `results/exp_003_semantic/per_question.jsonl` — NEW, 139 rows (incremental writes survived attempt 1's kill).
- `results/leaderboard.json` — refreshed (`last_updated` 2026-09-07T00:40:03); `chunking_content` first winner exp_003 (0.5612); `end_to_end` flips to exp_003 (faithfulness 0.8932).
- `results/leaderboard_snapshots/leaderboard_20260907_004003.json` — NEW immutable snapshot.
- `docs/experiments/exp_003_semantic/analysis.md` — full analysis (headline, per-type, per-ticker, 4 lessons, run notes, decision).
- `docs/progress/STEP_008_*` (this file) + `PROGRESS.md` index update.
- No code changed (runner, chunker, matcher untouched — same path as smoke).
- NOT committed: `results/smoke/*` (ephemeral), `data/runtime_costs.jsonl` (gitignored), `data/eval/qa_pairs.limit5.jsonl` (check `git status`; regenerable if dirty).

### 3. How it works (the run)
```bash
$env:CHUNKER_STRATEGY='semantic'; uv run python -m finrag.cli.eval --exp exp_003_semantic
uv run python tests/eval/update_leaderboard.py
```
- Attempt 1 hit the 90-min tool timeout mid-RAGAS (retrieval+generation for all 139 done; per-Q file complete at 139 lines; no CSV row since CLI appends after RAGAS). Attempt 2 reran fully (6264.5s) — chosen over salvaging because per-Q lacks retrieved texts and row cost needed for an exact canonical row.
- CSV header fix: CLI's `DictWriter(fieldnames=14)` appended a 14-value row under a 12-col header; `DictReader`-based readers (leaderboard) would have dropped the content values under a `None` key. Fixed by extending the header + padding frozen rows (see §5).

### 4. Result / numbers
139 Q, 20 filings, **6858 chunks**; cr=0.7562, fa=**0.8932 (track best)**, ar=0.7103; hit@5=0.3237 / cite=0.2302 (chunk_id artifacts); **hit@5_content=0.5612, cite_content=0.6691**; 8861.8ms/Q; $0.0301 (generation-only accounting). Per-type content: lookup 0.657, section 0.644, synthesis **0.556** (best synthesis yet), OOS hit_content 0.000 (placeholder-span quirk, non-OOS = 0.645). Worst tickers AMZN/KO/WMT (narrative skew persists). Deterministic chunk counts across attempts (JPM 916, GS 782, AAPL 141).

### 5. Evaluation/methods changes (user asked: track everything)
1. **Ledger schema 12→14 cols** (this step, §2). Old rows: values identical, content = empty (None). Forward-compatible per ADR-003/SCHEMA rule (append at end).
2. **Leaderboard**: `chunking_content` winner exp_003 (was null); `end_to_end` exp_003 (was exp_001). Rolling file overwritten + immutable snapshot (by design).
3. **Methods quirks found, NOT fixed** (ledger immutable; fixes need re-runs): (a) OOS `source_span='<no relevant span>'` defeats the empty-span OOS branch → propose STEP_009 matcher treats placeholder as empty; (b) Vertex generator always cites top-5 → chunk_id OOS cite structurally 0. Both documented in `analysis.md` §4.

### 6. How to recall
- STEP file: `docs/progress/STEP_008_exp003_full_run.md`
- Row: `results/experiments.csv` line 4; commit diff shows header migration explicitly
- Leaderboard: `results/leaderboard.json` + `results/leaderboard_snapshots/leaderboard_20260907_004003.json`
- Exp: `docs/experiments/exp_003_semantic/analysis.md`
- Reproduce: command in §3 (costs ~$0.06-0.08 double-run; normally one pass ~$0.03 + RAGAS judge)

### 7. Next step (STEP_009 candidate)
1. Runner micro-fix: treat `'<no relevant span>'` as empty in `hit_at_5_content`/OOS logic + test; re-run exp_003 (or carry fix into exp_004) so OOS content-hit is honest.
2. exp_004 structural: section-aware budgets aimed at context_recall + fewer chunks (P99 / per-section caps), per analysis.md decision.
