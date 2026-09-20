# Result snapshots — point-in-time preservation for later comparison

Ephemeral but valuable artifacts are snapshotted into git (force-added;
they stay gitignored day-to-day so normal work never touches them).
Each entry below is a full comparison baseline: ledger hash pins the
numbers, per-Q JSONLs pin every answer, smoke dirs pin the proofs.

## How to compare later

```bash
git show <snapshot-commit>:results/experiments.csv | sha256sum   # verify ledger unchanged
git diff <snap1> <snap2> -- results/experiments.csv              # what moved between snapshots
python -c "import json;[print(json.loads(l)['qid'], json.loads(l)['hit_at_5_content']) for l in open('results/exp_021_hybrid_rrf/per_question.jsonl')]"
# per-Q replays: join on qid across results/<exp>/per_question.jsonl (schema: qid, qa_type, hit_at_5_content, citation_accuracy_content, retrieved_chunk_ids, answer, latency_ms)
```

## Snapshots

### 2026-09-20 (`87c8a4f`) — full project baseline, STEP_001…045 complete
- Purpose: everything the project ever measured, frozen for multi-purpose reuse.
- Contents (30 files): all `results/smoke/*` proofs (attach, per-exp smokes,
  both nightly guards incl. 2026-09-20 post-Vertex-fix), `results/benchmarks/*`
  (qdrant/weaviate/vertex-search), `data/eval/qa_pairs.limit2.jsonl`,
  `logs/nightly.log` (DRIFT-OK run 2026-09-20 13:32).
- Already-tracked companions (not in this commit, same baseline): `results/experiments.csv`
  (13 rows), `results/leaderboard.json` + `results/leaderboard_snapshots/*`,
  all `results/<exp>/per_question.jsonl`, `tests/eval/` harness, `data/eval/qa_pairs.jsonl`.
- Integrity (SHA256 at snapshot time):
  - `results/experiments.csv`: `A00B8A800BEFD7374892C50F0BD67440297EB07981AAFA60716E1E45AA1F8BBF`
  - `results/leaderboard.json`: `90579732F3E147770BC01EFBE64EB5D93BA77B0DCC936738901FC309FB4089E3`
  - `data/eval/qa_pairs.jsonl`: `67694A89C8C42B5E2B486D3304659E9B9F8310072A4685EE323735F7FA564924`
- Note: `logs/nightly.log` keeps growing (scheduler appends nightly) — this
  commit pins it at the STEP_044 verification run. Re-snapshot only if a
  breach ever needs preserving (`results/drift_alerts.jsonl` is tracked anyway).
