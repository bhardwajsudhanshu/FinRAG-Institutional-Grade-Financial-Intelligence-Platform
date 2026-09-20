# STEP_044 — Nightly cron activated (Task Scheduler live, DRIFT-OK)

- **Date:** 2026-09-20
- **Git commit:** PENDING (this step)
- **Goal:** The drift guard runs itself. No ledger change.
- **Roadmap phase:** Open row → nightly cron activation (now DONE; 2 Open items left)

### 1. Why
`nightly.ps1` + runbook existed since STEP_027 but registration was a manual 4-step procedure nobody had executed. Unregistered guard = no guard.

### 2. What changed (files — this commit)
- `scripts/register_nightly_task.ps1` (new) — idempotent Task Scheduler registration: task `FinRAG-nightly-smoke`, daily 02:30, wake-to-run, 1h cap, exit code mirrors drift. ASCII-only (an em-dash killed PS 5.1 parsing mid-step — fixed before registering).
- `docs/02_nightly_ops.md` — Scheduling section now one command + disable/remove; manual path kept as fallback note.
- `README.md` — Ops row notes scheduler active; Open row drops nightly cron.
- `docs/progress/STEP_044_*` (this file) + `PROGRESS.md` index update.
- NOT changed: code, ledger (13 rows), leaderboard, eval set, guard thresholds. Live proof logs stay in untracked `logs/nightly.log`.

### 3. How to verify
```powershell
Get-ScheduledTask -TaskName FinRAG-nightly-smoke  # Ready, next run daily 02:30
powershell -ExecutionPolicy Bypass -File scripts/register_nightly_task.ps1  # re-run = refresh, idempotent
```

### 4. Result
- Payload verified live BEFORE registering: `nightly.ps1` exit 0, DRIFT-OK vs exp_021 (~5 min, ~$0.005, Vertex key from STEP_043).
- Task registered and confirmed: `FinRAG-nightly-smoke`, State Ready, next run 2026-09-21 02:30.

### 5. How to recall
- STEP file: `docs/progress/STEP_044_nightly_cron.md`
- Register script: `scripts/register_nightly_task.ps1`
- Guard entrypoint: `scripts/nightly.ps1` → `logs/nightly.log`; alerts: `results/drift_alerts.jsonl` (tracked)

### 6. Next step (STEP_045 candidate)
Remaining Open row: hybrid+multiquery/HyDE combos (low priority, ~$ Vertex) or auto-router/semantic cache. Recommend auto-router/semantic cache (free to build offline, serves every ask).
