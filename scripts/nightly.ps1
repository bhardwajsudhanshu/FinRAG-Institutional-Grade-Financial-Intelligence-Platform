# Nightly guard entrypoint for Windows Task Scheduler (STEP_027).
# Task action: powershell.exe -ExecutionPolicy Bypass -File <project>/scripts/nightly.ps1
# Runs the hybrid 10-Q smoke + drift check directly (no `make` needed —
# `make` isn't on Windows PATH; the Makefile is WSL-first).
# Logs to logs/nightly.log. Exit code mirrors the drift check
# (0 ok, 1 breach, 2 error) so the scheduler history shows verdicts.

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -LiteralPath $root
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

function Log($msg) {
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg" | Out-File -Append -Encoding utf8 "logs/nightly.log"
}

Log "nightly-smoke start"
# Pin all four (machine OS env exports invalid VECTORDB_BACKEND=chroma).
$env:CHUNKER_STRATEGY = "naive"
$env:RETRIEVAL_STRATEGY = "hybrid"
$env:RERANK_BACKEND = "none"
$env:VECTORDB_BACKEND = "in-memory"
& uv run python -m finrag.cli.eval --exp nightly_guard --limit 10 --smoke >> "logs/nightly.log" 2>&1
& uv run python scripts/check_drift.py --ledger results/experiments.csv --baseline-exp exp_021_hybrid_rrf --candidate results/smoke --alert-log results/drift_alerts.jsonl >> "logs/nightly.log" 2>&1
$code = $LASTEXITCODE
Log "nightly-smoke exit=$code"
exit $code
