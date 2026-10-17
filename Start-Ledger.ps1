<#
.SYNOPSIS
Starts the Ledger app from one place: backend and frontend, plus the LAN gateway with -Remote.

.DESCRIPTION
Starts the backend (`python -m app`) and the frontend (a `vite` dev server, or a `vite build` +
`vite preview`, per -Mode) - each the same separate process CLAUDE.md's "Setup & Run" describes,
just launched together. Backend and frontend each open in their own window so their logs and Ctrl+C
stay independent. Their window PIDs are recorded to the root .ledger-run.json (gitignored) so the
paired Stop-Ledger.ps1 can stop exactly these two windows (and their child processes) without
touching any other window you have open.

The gateway is no longer part of the default start. It comes up through Remote mode (the switch in
the dashboard or the desktop widget), which starts Docker if needed and the gateway and shuts them
down again after 8 hours. -Remote does the same from here: it asks the backend to turn Remote mode
on, waits until it is ready, and prints the sign-in link/QR the same way gateway\Start-Gateway.ps1
does. The backend, not this script, owns the gateway: it is started and stopped by Remote mode.

-Mode picks how the backend and frontend run - it has no effect on the gateway, which always starts
the same way either way. `build` (the default, matching normal local use) runs `npm run build` once
and then serves the built app via `vite preview`, which doesn't rebuild on save, and starts the
backend without `--reload`. `dev` runs `vite`'s hot-reloading dev server instead, and starts the
backend with uvicorn's `--reload` (restarts on saved changes under `api/`) - for actively working on
either side. `--reload` re-imports the app fresh per restart, so the backend's own startup
banner/token print (see `app/cli.py`'s `main()`) is only ever accurate for the first start of a
`-Mode dev` session.

Port precedence per BackendPort/FrontendPort/GatewayPort (highest wins): an explicit -*Port
parameter, then the repo root's .env (see .env.example), then an already-set
BACKEND_PORT/FRONTEND_PORT/GATEWAY_PORT environment variable, then the hardcoded defaults (8501,
4173, 8080) - the same precedence gateway\Start-Gateway.ps1 uses.

The gateway needs Docker Desktop. Without -Remote the app is reachable from this machine only (see
CLAUDE.md's "From another device on your network"). The backend learns the gateway port from the
root .env, then GATEWAY_PORT, so an explicit -GatewayPort only reaches it when .env doesn't set one.

-InstallBackupTask registers (or updates) the daily Task Scheduler entry that keeps
`api/.history/history.db` accumulating between runs of this app - the same thing
`hooks\ledgerScripts\Install-HistoryBackupTask.ps1` does on its own, wired in here as a one-flag
convenience. It runs before anything else starts, and a failure there doesn't stop the
backend/frontend/gateway from still starting normally. The paired Stop-Ledger.ps1's
-UninstallBackupTask removes it again.

.PARAMETER Mode
'build' (default): build the frontend once and serve it with `vite preview`; backend without
--reload. 'dev': hot-reloading vite dev server; backend with --reload.

.PARAMETER Remote
Also turn Remote mode on: start Docker if needed and the gateway, wait until it is ready, and print
the sign-in link/QR. Switch it off from the dashboard or the widget (or run Stop-Ledger.ps1).

.PARAMETER NoGateway
Accepted for old command lines and does nothing: the gateway is no longer started by default.

.PARAMETER InstallBackupTask
Also register (or update) the daily history-backup scheduled task - see
hooks\ledgerScripts\Install-HistoryBackupTask.ps1.

.PARAMETER BackendPort
Port for the backend API. Default 8501.

.PARAMETER FrontendPort
Port for the frontend. Default 4173.

.PARAMETER GatewayPort
Port the gateway is published on. Default 8080. Avoid Chromium's restricted ports (e.g. 10080).

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Start-Ledger.ps1
Build mode: backend + frontend, this machine only.

.EXAMPLE
.\Start-Ledger.ps1 -Mode dev
Backend and frontend as hot-reloading dev servers.

.EXAMPLE
.\Start-Ledger.ps1 -Remote
Backend + frontend, then Remote mode on with its sign-in QR.

.EXAMPLE
.\Start-Ledger.ps1 -BackendPort 9000 -FrontendPort 5000 -GatewayPort 9090
Override every port.

.EXAMPLE
.\Start-Ledger.ps1 -InstallBackupTask
Also register the daily history-backup scheduled task, then start as normal.

.LINK
.\Stop-Ledger.ps1 stops everything this script started (and, with -UninstallBackupTask, removes the
scheduled task this script's -InstallBackupTask installs).
#>

param(
    [ValidateSet('dev', 'build')]
    [string]$Mode = 'build',
    [switch]$Remote,
    [switch]$NoGateway,
    [switch]$InstallBackupTask,
    [int]$BackendPort,
    [int]$FrontendPort,
    [int]$GatewayPort,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

$envFileValues = @{}
$rootEnvFile = Join-Path $PSScriptRoot '.env'
if (Test-Path $rootEnvFile) {
    foreach ($line in Get-Content $rootEnvFile) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$' -and $line -notmatch '^\s*#') {
            $envFileValues[$Matches[1]] = $Matches[2]
        }
    }
}

function Resolve-Port {
    param([int]$Explicit, [string]$Name, [int]$Default)
    if ($Explicit) { return $Explicit }
    if ($envFileValues.ContainsKey($Name)) { return [int]$envFileValues[$Name] }
    $existing = [Environment]::GetEnvironmentVariable($Name)
    if ($existing) { return [int]$existing }
    return $Default
}

$BackendPort = Resolve-Port -Explicit $BackendPort -Name 'BACKEND_PORT' -Default 8501
$FrontendPort = Resolve-Port -Explicit $FrontendPort -Name 'FRONTEND_PORT' -Default 4173
$GatewayPort = Resolve-Port -Explicit $GatewayPort -Name 'GATEWAY_PORT' -Default 8080

$venvPython = Join-Path $PSScriptRoot 'api\.venv\Scripts\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

if ($NoGateway) {
    Write-Host "Note: -NoGateway does nothing now - the gateway only starts with Remote mode (-Remote)."
}

if ($InstallBackupTask) {
    Write-Host "Installing the daily history-backup scheduled task..."
    try {
        & (Join-Path $PSScriptRoot 'hooks\ledgerScripts\Install-HistoryBackupTask.ps1')
    } catch {
        Write-Warning "Failed to install the history-backup task: $_"
    }
}

# The backend reads these when Remote mode starts the gateway.
$env:GATEWAY_PORT = $GatewayPort

Write-Host "Starting backend on port $BackendPort in $Mode mode (new window)..."
$backendReloadFlag = if ($Mode -eq 'dev') { ' --reload' } else { '' }
$backendCommand = "Set-Location '$PSScriptRoot\api'; & '$python' -m app --port $BackendPort --frontend-port $FrontendPort$backendReloadFlag"
$backendProc = Start-Process powershell -ArgumentList '-NoExit', '-Command', $backendCommand -PassThru

Write-Host "Starting frontend on port $FrontendPort in $Mode mode (new window)..."
if ($Mode -eq 'dev') {
    $frontendCommand = "Set-Location '$PSScriptRoot\web'; `$env:BACKEND_PORT = '$BackendPort'; npm run dev -- --port $FrontendPort"
} else {
    $frontendCommand = "Set-Location '$PSScriptRoot\web'; `$env:BACKEND_PORT = '$BackendPort'; npm run build; if (`$LASTEXITCODE -eq 0) { npm run preview -- --port $FrontendPort } else { Read-Host 'Build failed - press Enter to close' }"
}
$frontendProc = Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCommand -PassThru

# Recorded so Stop-Ledger.ps1 can find exactly these two windows later.
[PSCustomObject]@{
    BackendPid  = $backendProc.Id
    FrontendPid = $frontendProc.Id
    StartedAt   = (Get-Date).ToString('o')
} | ConvertTo-Json | Set-Content -Path (Join-Path $PSScriptRoot '.ledger-run.json') -Encoding utf8

Write-Host "Frontend will be at http://localhost:$FrontendPort"

if (-not $Remote) {
    Write-Host "Reachable from this machine only. Turn on Remote mode (dashboard or widget), or run with -Remote, for the gateway."
    exit 0
}

$backendUrl = "http://127.0.0.1:$BackendPort"

# The backend is starting in its own window; wait for it to answer before asking it for anything.
function Get-RemoteMode {
    try {
        return (Invoke-RestMethod -Uri "$backendUrl/api/meta" -TimeoutSec 3).remote_mode
    } catch {
        return $null
    }
}

Write-Host "Waiting for the backend..."
$deadline = (Get-Date).AddSeconds(60)
while ($null -eq (Get-RemoteMode) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 1
}
if ($null -eq (Get-RemoteMode)) {
    Write-Warning "The backend didn't answer on port $BackendPort - Remote mode was not turned on."
    exit 1
}

Write-Host "Turning Remote mode on (Docker and the gateway start if needed)..."
try {
    Invoke-RestMethod -Method Post -Uri "$backendUrl/api/remote-mode" -ContentType 'application/json' `
        -Headers @{ 'X-Requested-With' = 'ledger' } -Body '{"enabled": true}' | Out-Null
} catch {
    Write-Warning "Could not turn Remote mode on: $_"
    exit 1
}

# Docker Desktop can take minutes to come up, so give it room.
$deadline = (Get-Date).AddMinutes(5)
$lastStep = $null
do {
    Start-Sleep -Seconds 2
    $status = Get-RemoteMode
    if ($status -and $status.state -eq 'starting' -and $status.step -ne $lastStep) {
        $lastStep = $status.step
        Write-Host "  starting: $lastStep"
    }
} while ($status -and $status.state -eq 'starting' -and (Get-Date) -lt $deadline)

if (-not $status -or $status.state -ne 'ready') {
    $reason = if ($status -and $status.reason) { $status.reason } else { 'it did not become ready in time' }
    Write-Warning "Remote mode did not start: $reason. Backend and frontend are still up in their own windows."
    exit 1
}

& $python (Join-Path $PSScriptRoot 'api\gateway_signin.py') --gateway-port $GatewayPort
exit $LASTEXITCODE
