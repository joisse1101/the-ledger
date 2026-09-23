<#
Stops what Start-Ledger.ps1 started: the backend and frontend windows (found via the PIDs
Start-Ledger.ps1 recorded to the root .ledger-run.json, removed once used) and the gateway
container (`docker compose down`, same as gateway\Stop-Gateway.ps1) - all three, in one call.

Only ever touches processes Start-Ledger.ps1 itself launched - it won't find or stop a
backend/frontend you started by hand in your own terminal (there's no .ledger-run.json for those).
Each window is stopped as a whole process tree (its `npm`/`vite`/`python` children included), not
just the outer PowerShell window.

Usage:
  .\Stop-Ledger.ps1              # stop backend + frontend + gateway
  .\Stop-Ledger.ps1 -NoGateway   # leave the gateway container running
#>

param(
    [switch]$NoGateway
)

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
