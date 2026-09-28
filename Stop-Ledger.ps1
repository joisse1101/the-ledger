<#
.SYNOPSIS
Stops what Start-Ledger.ps1 started: backend, frontend and gateway.

.DESCRIPTION
Stops the backend and frontend windows (found via the PIDs Start-Ledger.ps1 recorded to the root
.ledger-run.json, removed once used) and the gateway container (`docker compose down`, same as
gateway\Stop-Gateway.ps1) - all three, in one call.

Only ever touches processes Start-Ledger.ps1 itself launched - it won't find or stop a
backend/frontend you started by hand in your own terminal (there's no .ledger-run.json for those).
Each window is stopped as a whole process tree (its `npm`/`vite`/`python` children included), not
just the outer PowerShell window.

-UninstallBackupTask removes the daily history-backup Scheduled Task Start-Ledger.ps1's
-InstallBackupTask (or hooks\ledgerScripts\Install-HistoryBackupTask.ps1 directly) installs - opt-in
only, since that task is meant to keep running independently of whether the app itself is up.

.PARAMETER NoGateway
Leave the gateway container running.

.PARAMETER UninstallBackupTask
Also remove the daily history-backup scheduled task - see
hooks\ledgerScripts\Uninstall-HistoryBackupTask.ps1.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Stop-Ledger.ps1
Stop backend + frontend + gateway.

.EXAMPLE
.\Stop-Ledger.ps1 -NoGateway
Stop backend + frontend, leave the gateway container running.

.EXAMPLE
.\Stop-Ledger.ps1 -UninstallBackupTask
Also remove the daily history-backup scheduled task.

.LINK
.\Start-Ledger.ps1's -InstallBackupTask installs the scheduled task this script's
-UninstallBackupTask removes.
#>

param(
    [switch]$NoGateway,
    [switch]$UninstallBackupTask,
    [switch]$Help
)

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

if ($UninstallBackupTask) {
    Write-Host "Removing the daily history-backup scheduled task..."
    try {
        & (Join-Path $PSScriptRoot 'hooks\ledgerScripts\Uninstall-HistoryBackupTask.ps1')
    } catch {
        Write-Warning "Failed to remove the history-backup task: $_"
    }
}

$stateFile = Join-Path $PSScriptRoot '.ledger-run.json'

if (Test-Path $stateFile) {
    $state = Get-Content $stateFile -Raw | ConvertFrom-Json
    $targets = @(
        [PSCustomObject]@{ Name = 'backend'; Id = $state.BackendPid }
        [PSCustomObject]@{ Name = 'frontend'; Id = $state.FrontendPid }
    )
    foreach ($target in $targets) {
        if ($target.Id -and (Get-Process -Id $target.Id -ErrorAction SilentlyContinue)) {
            Write-Host "Stopping $($target.Name) (PID $($target.Id)) and its child processes..."
            & taskkill.exe /PID $target.Id /T /F | Out-Null
        } else {
            Write-Host "$($target.Name) isn't running (PID $($target.Id)) - nothing to stop."
        }
    }
    Remove-Item $stateFile -Force
} else {
    Write-Warning "No .ledger-run.json found - nothing recorded to stop for the backend/frontend (were they started with Start-Ledger.ps1?)."
}

if ($NoGateway) {
    Write-Host "Leaving the gateway running (-NoGateway)."
    exit 0
}

Write-Host "Stopping gateway..."
Push-Location (Join-Path $PSScriptRoot 'gateway')
try {
    docker compose down -v
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not stop the gateway (is Docker Desktop running?)."
}
