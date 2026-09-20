# Register (or refresh) the FinRAG nightly guard in Windows Task Scheduler (STEP_044).
# Idempotent: removes the existing task first, then registers fresh.
# The task runs scripts/nightly.ps1 daily at 02:30, logs to logs/nightly.log,
# wakes the machine, and is killed if it exceeds 1h. Exit code mirrors the
# drift check (0 ok, 1 breach, 2 error) — visible in scheduler History.
#
# Run once from an elevated prompt (admin needed to create the task):
#   powershell -ExecutionPolicy Bypass -File scripts/register_nightly_task.ps1
# Remove:
#   Unregister-ScheduledTask -TaskName "FinRAG-nightly-smoke" -Confirm:$false

$ErrorActionPreference = "Stop"
$taskName = "FinRAG-nightly-smoke"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root "scripts\nightly.ps1"

if (-not (Test-Path -LiteralPath $script)) {
    throw "nightly.ps1 not found at $script"
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$script`"" `
    -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At "02:30"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -WakeToRun -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description "FinRAG nightly drift guard (STEP_044)" | Out-Null

Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State, @{N="NextRun";E={(($_ | Get-ScheduledTaskInfo).NextRunTime)}}
Write-Output "Registered. Logs: $root\logs\nightly.log - disable: Disable-ScheduledTask -TaskName $taskName"
