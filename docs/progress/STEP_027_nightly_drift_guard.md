# STEP_027 — Nightly drift guard (protects the ledger while we sleep)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Scheduler-ready drift detection with proven live run; no false-alarm design shipped.
- **Roadmap phase:** Ops (ledger protection; first non-quality, non-serving system)

### 1. Why
9 ledger rows are now the project's crown jewels and every Vertex/model/
dependency change can silently move them. A guard that cries wolf nightly
is worse than none — this step built the checker, watched it false-alarm
on real data, and fixed the statistics before scheduling anything.

### 2. What changed (files — this commit)
- `scripts/check_drift.py` — NEW: ledger-baseline vs candidate comparison (7 metrics + latency), exit 0/1/2, JSON verdict to stdout/--out, breach appends to --alert-log. Flat `--tol 0.05` + binomial noise floor `max(tol, 1.96·sqrt(p(1-p)/n))`; None-safe throughout; `--candidate` accepts a file or a smoke-run directory (newest wins — dirs accumulate nightly).
- `scripts/nightly.ps1` — NEW Task Scheduler entrypoint (no `make` dependency: `make` isn't on Windows PATH — probed; runs uv directly with all four pins, logs to `logs/nightly.log`, exit mirrors drift).
- `tests/test_drift.py` — NEW, 17 tests (pass/noise/improvement, breach incl. latency, skips, noise-floor small-vs-large-n + real-collapse, directory resolution, CLI exit codes).
- `Makefile` — `nightly-smoke` (10-Q hybrid + drift vs exp_021) + `drift-check` (CAND/BASE); `.PHONY` completed (also added pre-existing-but-unlisted `eval-smoke`, `eval-nightly`, `patch-ragas`).
- `docs/02_nightly_ops.md` — NEW runbook (two tiers, thresholds, Task Scheduler + cron, alerting, explicit non-goals).
- `docs/progress/STEP_027_*` (this file) + `PROGRESS.md` index update.
- NOT changed: ledger (9 rows), leaderboard, eval set, runner. No code in the RAG path at all.
- NOT committed: `results/smoke/nightly_guard_*/` (ephemeral proof), `results/drift_alerts.jsonl` (see §5 — false-alarm line deleted as superseded).

### 3. How it works
Tier 1 (`make nightly-smoke`, ~5 min, ~$0.005): hybrid 10-Q smoke → drift check vs exp_021 → exit code. Tier 2 (weekly, manual): full 139-Q smoke-mode run + `make drift-check`. Scheduler keys off exit codes; breaches append JSONL alerts.

### 4. How to verify
```bash
uv run pytest tests/test_drift.py -q
uv run ruff check scripts/check_drift.py tests/test_drift.py  # (no Makefile — ruff parses it as Python)
```

### 5. Result / numbers
- Unit: 17 passed. Ruff: own RUF002 (× char) fixed; shared E402 only.
- Live proof 2026-09-07 (222s, $0.0028, 10 Q / AAPL+AMZN / 229 chunks): FIRST verdict was DRIFT-BREACH (recall -10.6pp, hit@5 -7.6pp) on a healthy system — 10-Q noise, each Q worth 10pp. Fixed with the noise floor; re-verdict DRIFT-OK (thresholds 0.18–0.30 shown per metric). Content metrics were fine throughout (0.80 vs 0.8129) — the breach was all small-n RAGAS/chunk_id wobble.
- Deleted locally: the one `drift_alerts.jsonl` false-alarm line (superseded logic — the incident lives here instead, not in the alert ledger).
- Own mistakes recorded: (a) ate a newline with an empty edit (fixed immediately); (b) passed `Makefile` to `ruff check` (237 bogus errors — ruff only speaks Python); (c) PowerShell `tail`/`wc`/`head` don't exist (repeated offense — Select-Object only).

### 6. How to recall
- STEP file: `docs/progress/STEP_027_nightly_drift_guard.md`
- Code: `scripts/check_drift.py`; entry: `scripts/nightly.ps1`; runbook: `docs/02_nightly_ops.md`
- Tests: `tests/test_drift.py`
- Proof: `results/smoke/nightly_guard_20260907_211629/` (untracked)

### 7. Next step (STEP_028 candidate)
Vertex Search pre-deploy benchmark or README/deploy-guide polish or parent-doc/multi-query retrieval (synthesis still trails). Recommend deploy polish: the system is done enough to deserve a README that sells it (sweep table, architecture diagram, cost ledger).
