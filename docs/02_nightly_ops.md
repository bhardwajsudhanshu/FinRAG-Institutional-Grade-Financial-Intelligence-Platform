# Nightly Ops — Drift Guard Runbook (STEP_027)

Two tiers protect the 9-row ledger while you sleep. Both are cheap by
design; neither touches `results/experiments.csv` (smoke writes go to
`results/smoke/`, which the canonical ledger never reads).

## Tier 1 — nightly smoke guard (every night, ~5 min, ~$0.005)

```bash
make nightly-smoke
```

Proven live 2026-09-07 (STEP_027): 222s wall, $0.0028, 10 Q / 2 filings /
229 chunks, DRIFT-OK vs exp_021 after the noise-floor fix (first version
false-alarmed twice on 10-Q noise — the fix is the point of the story).

Runs: hybrid 10-Q smoke (`nightly_guard`, in-memory, no rerank) →
`scripts/check_drift.py` vs `exp_021_hybrid_rrf` baseline → exit 0
(DRIFT-OK) or exit 1 (DRIFT-BREACH + appends `results/drift_alerts.jsonl`).

Catches: expired GCP creds, Vertex API changes/model removals, EDGAR or
parser breakage (new filings), dependency rot. Does NOT catch: slow
metric decay (10 Q is too few — that's Tier 2's job).

## Tier 2 — weekly full hybrid (Sundays, ~50 min, ~$0.10)

```bash
CHUNKER_STRATEGY=naive RETRIEVAL_STRATEGY=hybrid RERANK_BACKEND=none VECTORDB_BACKEND=in-memory \
  uv run python -m finrag.cli.eval --exp weekly_guard --limit 0 --smoke
make drift-check CAND=results/smoke/weekly_guard_<ts>/smoke_experiments.csv BASE=exp_021_hybrid_rrf
```

(Pin all four vars — machine OS env exports invalid `chroma`.)
Full 139-Q power: 5pp+ decay on any tracked metric breaches.

## Thresholds (locked here, overridable via CLI flags)

- Metric drop beyond `--tol 0.05` vs baseline → BREACH. Improvements are info-only.
- Small-n honesty (STEP_027 lesson): the effective threshold is
  `max(tol, 1.96·sqrt(p·(1-p)/n))` — at n=10 the noise floor is ~0.2-0.3,
  so Tier 1 only catches catastrophe. That is its honest job: infra
  failure (auth expiry, API removal, parser breakage) craters metrics or
  crashes the run — both fail loudly. Precision decay is Tier 2's job.
- Latency beyond `--latency-factor 2.0` × baseline → BREACH.
- Empty/None on either side → SKIP (frozen rows lack content columns).

## Scheduling

**Windows Task Scheduler** (this machine):
1. Task Scheduler → Create Task → Triggers: Daily 02:00.
2. Action: `powershell.exe -ExecutionPolicy Bypass -File <project>/scripts/nightly.ps1`
   (provided — runs `make nightly-smoke`, logs to `logs/nightly.log`, exit code mirrors drift).
3. Conditions: Wake to run; stop if running > 1h. History enabled to audit.

**cron** (Linux/macOS): `0 2 * * * cd <project> && make nightly-smoke >> logs/nightly.log 2>&1`

**Alerting:** exit 1 appends to `results/drift_alerts.jsonl` (tracked — alerts are audit trail). Check the file mornings-after, or point a mailer at non-zero exits. Pager integration deferred (no users yet).

## What the guard does NOT do

- Never appends to `results/experiments.csv` or rebuilds the leaderboard (smoke routing, STEP_006 rule).
- Never pages anyone (no on-call). It records; humans decide.
- Reranked flagship is NOT guarded nightly ($0.17 × 365 = $62/yr is fine actually — but 2h/night blocks the runner; weekly full-rerank is the compromise, unscheduled — run manually).
