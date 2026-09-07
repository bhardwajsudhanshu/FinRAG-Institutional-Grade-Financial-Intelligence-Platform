# STEP_028 — Deploy polish (README sells the sweep)

- **Date:** 2026-09-07
- **Git commit:** PENDING (this step)
- **Goal:** Front door worthy of the system: README states reality + deploy guide makes production reproducible. No ledger change.
- **Roadmap phase:** Polish (12-week plan's Week 12, pulled forward — the system earned it)

### 1. Why
The repo's front page still described a 12-week *plan* ("will produce…")
while the ledger holds 9 experiments and a 5/5 sweep. Every new reader
(and future-you) should land on results first, then the machine that
produced them.

### 2. What changed (files — this commit)
- `README.md` — rewritten: cited-answer demo, 9-row results table (locked numbers), ASCII architecture, quickstart (env → docker → ingest → serve/ui → verify/guard), actual project structure, honest roadmap table (done/deferred), both Windows gotchas, ADR index, pointer to PROGRESS.md.
- `docs/03_deploy.md` — NEW: 3 serving profiles with measured cost/latency, production checklist (env/infra/serve/guard/costs), 4 explicit NOTs, scaling notes (incl. filed-not-built persistent-collection work for a real fleet).
- `docs/01_setup.md` — one stale line fixed (`no tests yet` → 160 tests).
- `docs/progress/STEP_028_*` (this file) + `PROGRESS.md` index update.
- NOT changed: code, ledger (9 rows), leaderboard, eval set. Nothing to unit-test (docs only — full suite untouched and still green from STEP_027).

### 3. Numbers audit (README claims vs locked rows)
All table values copied from `results/experiments.csv` rows 1–9 as
recorded in STEP files (exp_001 0.6043/0.5612 → exp_030 0.8849/0.7266).
Cost/latency profiles from smoke/full-run tables ($0.0003/Q demo,
$0.0012/Q flagship, $0.171 all-in rerank run). No new measurement in
this step — packaging only.

### 4. How to verify
```bash
git diff README.md  # reality check against results/experiments.csv
uv run pytest tests -q  # untouched, still green (ran STEP_027)
```

### 5. Result
README leads with the sweep, not the plan; deploy path reproducible from
two docs (01_setup + 03_deploy) + runbook (02_nightly_ops).

### 6. How to recall
- STEP file: `docs/progress/STEP_028_deploy_polish.md`
- Front door: `README.md`; ops: `docs/03_deploy.md`

### 7. Next step (STEP_029 candidate)
Vertex Search pre-deploy benchmark (last unmeasured store) or parent-doc/multi-query retrieval (synthesis still trails) or FastAPI `--workers`/persistent-collection hardening from the deploy notes. Recommend Vertex Search: it closes the vector-DB phase for good (~$1 exposure, same-day teardown).
