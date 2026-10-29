<#
.SYNOPSIS
Starts the Ledger app from one place: backend, frontend and the desktop widget, plus the LAN gateway with -Remote.

.DESCRIPTION
In order: checks that Python and Node are installed (and Docker with -Remote), repairs any missing or
out-of-date dependency (the backend's venv, the frontend and widget packages, the Electron binary),
chooses the ports, then starts the backend (`python -m app`), the frontend (a `vite` dev server, or a
`vite build` + `vite preview`, per -Mode) and, once the backend answers, the desktop widget. It then
checks that each one is actually up, prints a summary, and exits non-zero if any is not.

Backend and frontend each open in their own window so their logs and Ctrl+C stay independent. Their
window PIDs are recorded to the root .ledger-run.json (gitignored) so the paired Stop-Ledger.ps1 can
stop exactly these windows (and their child processes) without touching any other window you have
open. A backend that is already answering on the chosen port is reused, not started a second time.

A missing prerequisite stops the start before anything is touched: the script names it, prints the
official page to install it from, and exits non-zero. A dependency that cannot be installed (for
example with no network) stops it the same way.

The gateway is no longer part of the default start. It comes up through Remote mode (the switch in
the dashboard or the desktop widget), which starts Docker if needed and the gateway and shuts them
down again after 8 hours. -Remote does the same from here: it asks the backend to turn Remote mode
on and waits until it is ready; the sign-in QR for other devices is then in the dashboard's
"Open on another device" dialog. The backend, not this script, owns the gateway: it is started and stopped by Remote mode.

-Mode picks how the backend and frontend run - it has no effect on the gateway, which always starts
the same way either way. `build` (the default, matching normal local use) runs `npm run build` once
and then serves the built app via `vite preview`, which doesn't rebuild on save, and starts the
backend without `--reload`. `dev` runs `vite`'s hot-reloading dev server instead, and starts the
backend with uvicorn's `--reload` (restarts on saved changes under `api/`) - for actively working on
either side. `--reload` re-imports the app fresh per restart, so the backend's own startup
banner (see `app/cli.py`'s `main()`) is only ever accurate for the first start of a
`-Mode dev` session.

Ports are chosen per BackendPort/FrontendPort/GatewayPort from the first of these that applies: an
explicit -*Port parameter, the repo root's .env (see .env.example), the port saved by an earlier run
(.ledger-ports.json, gitignored), or the first free port in 8501-8599, which is then saved so the
next run, the widget and the install scripts use the same one. A saved backend port that is busy is
reused when this app's backend holds it; any other saved port that is busy is replaced by a free one.

The gateway needs Docker Desktop. Without -Remote the app is reachable from this machine only (see
CLAUDE.md's "From another device on your network"). The backend learns the gateway port from the
root .env, then GATEWAY_PORT, so an explicit -GatewayPort only reaches it when .env doesn't set one.

.PARAMETER Mode
'build' (default): build the frontend once and serve it with `vite preview`; backend without
--reload. 'dev': hot-reloading vite dev server; backend with --reload.

.PARAMETER Remote
Also turn Remote mode on: start Docker if needed and the gateway, and wait until it is ready. Scan
the sign-in QR from the dashboard. Switch it off from the dashboard or the widget (or run Stop-Ledger.ps1).

.PARAMETER NoWidget
Don't start the desktop widget (and don't check its dependencies).

.PARAMETER NoGateway
Accepted for old command lines and does nothing: the gateway is no longer started by default.

.PARAMETER BackendPort
Port for the backend API. Default: the saved port, else the first free one in 8501-8599.

.PARAMETER FrontendPort
Port for the frontend. Default: the saved port, else the next free one in 8501-8599.

.PARAMETER GatewayPort
Port the gateway is published on. Default: the saved port, else the next free one in 8501-8599.
Avoid Chromium's restricted ports (e.g. 10080).

.PARAMETER StartupTimeoutSeconds
How long to wait for the backend, the frontend and the widget to come up before reporting them as
failed. Default 180 (a `-Mode build` start runs a full frontend build first).

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Start-Ledger.ps1
Build mode: backend + frontend + widget, this machine only.

.EXAMPLE
.\Start-Ledger.ps1 -NoWidget
Backend + frontend only.

.EXAMPLE
.\Start-Ledger.ps1 -Mode dev
Backend and frontend as hot-reloading dev servers.

.EXAMPLE
.\Start-Ledger.ps1 -Remote
Backend + frontend + widget, then Remote mode on with its sign-in QR.

.EXAMPLE
.\Start-Ledger.ps1 -BackendPort 9000 -FrontendPort 5000 -GatewayPort 9090
Override every port.

.LINK
.\Stop-Ledger.ps1 stops everything this script started.
#>

param(
    [ValidateSet('dev', 'build')]
    [string]$Mode = 'build',
    [switch]$Remote,
    [switch]$NoWidget,
    [switch]$NoGateway,
    [int]$BackendPort,
    [int]$FrontendPort,
    [int]$GatewayPort,
    [int]$StartupTimeoutSeconds = 180,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

. (Join-Path $PSScriptRoot 'scripts\Ledger-Common.ps1')

if (-not (Test-Prerequisites -Remote:$Remote)) { exit 1 }

$components = @('api', 'web')
if (-not $NoWidget) { $components += 'widget' }
try {
    Invoke-DependencyRepair -RepoRoot $PSScriptRoot -Component $components
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
    exit 1
}

$envFileValues = Read-EnvFile -Path (Join-Path $PSScriptRoot '.env')
$savedPorts = Get-SavedPorts

$backend = Resolve-LedgerPort -Explicit $BackendPort -Name 'BACKEND_PORT' -EnvFileValues $envFileValues `
    -SavedPorts $savedPorts -ReuseWhen { param($port) Test-LedgerBackend -Port $port }
$frontend = Resolve-LedgerPort -Explicit $FrontendPort -Name 'FRONTEND_PORT' -EnvFileValues $envFileValues `
    -SavedPorts $savedPorts -Exclude @($backend.Port)
$gateway = Resolve-LedgerPort -Explicit $GatewayPort -Name 'GATEWAY_PORT' -EnvFileValues $envFileValues `
    -SavedPorts $savedPorts -Exclude @($backend.Port, $frontend.Port)

$chosenPorts = [ordered]@{ BACKEND_PORT = $backend; FRONTEND_PORT = $frontend; GATEWAY_PORT = $gateway }
foreach ($name in $chosenPorts.Keys) {
    if ($chosenPorts[$name].Source -eq 'scanned') { Save-Port -Name $name -Port $chosenPorts[$name].Port }
}
$BackendPort = $backend.Port
$FrontendPort = $frontend.Port
$GatewayPort = $gateway.Port

$venvPython = Join-Path $PSScriptRoot 'api\.venv\Scripts\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

if ($NoGateway) {
    Write-Host "Note: -NoGateway does nothing now - the gateway only starts with Remote mode (-Remote)."
}

# The backend reads these when Remote mode starts the gateway.
$env:GATEWAY_PORT = $GatewayPort

$stateFile = Join-Path $PSScriptRoot '.ledger-run.json'
$previousState = if (Test-Path $stateFile) { Get-Content $stateFile -Raw | ConvertFrom-Json } else { $null }

$backendPid = $null
if (Test-LedgerBackend -Port $BackendPort) {
    Write-Host "Backend already running on port $BackendPort - reusing it."
    # Keep the PID an earlier run recorded, so Stop-Ledger.ps1 can still stop it.
    if ($previousState) { $backendPid = $previousState.BackendPid }
} else {
    Write-Host "Starting backend on port $BackendPort in $Mode mode (new window)..."
    $backendReloadFlag = if ($Mode -eq 'dev') { ' --reload' } else { '' }
    $backendCommand = "Set-Location '$PSScriptRoot\api'; & '$python' -m app --port $BackendPort --frontend-port $FrontendPort$backendReloadFlag"
    $backendPid = (Start-Process powershell -ArgumentList '-NoExit', '-Command', $backendCommand -PassThru).Id
}

Write-Host "Starting frontend on port $FrontendPort in $Mode mode (new window)..."
if ($Mode -eq 'dev') {
    $frontendCommand = "Set-Location '$PSScriptRoot\web'; `$env:BACKEND_PORT = '$BackendPort'; npm run dev -- --port $FrontendPort"
} else {
    $frontendCommand = "Set-Location '$PSScriptRoot\web'; `$env:BACKEND_PORT = '$BackendPort'; npm run build; if (`$LASTEXITCODE -eq 0) { npm run preview -- --port $FrontendPort } else { Read-Host 'Build failed - press Enter to close' }"
}
$frontendProc = Start-Process powershell -ArgumentList '-NoExit', '-Command', $frontendCommand -PassThru

$widgetDir = Join-Path $PSScriptRoot 'widget'
$widgetPid = $null

# Recorded so Stop-Ledger.ps1 can find exactly the processes this start launched.
function Save-RunState {
    [PSCustomObject]@{
        BackendPid  = $backendPid
        FrontendPid = $frontendProc.Id
        WidgetPid   = $widgetPid
        StartedAt   = (Get-Date).ToString('o')
    } | ConvertTo-Json | Set-Content -Path $stateFile -Encoding utf8
}
Save-RunState

# The widget starts its own hidden backend if none answers, so it waits for this one.
Write-Host "Waiting for the backend..."
$backendUp = Wait-Until -Condition { Test-LedgerBackend -Port $BackendPort } -TimeoutSeconds $StartupTimeoutSeconds

$widgetState = 'skipped'
if (-not $NoWidget -and $backendUp) {
    $runningWidgets = @(Get-RunningWidget -WidgetDir $widgetDir)
    if ($runningWidgets.Count -gt 0) {
        Write-Host "The widget is already running - leaving it alone."
        $widgetState = 'already running'
        # A widget an earlier start launched is still this start's to stop.
        if ($previousState -and ($previousState.WidgetPid -in $runningWidgets.ProcessId)) { $widgetPid = $previousState.WidgetPid }
    } else {
        Write-Host "Starting the widget..."
        try {
            & (Join-Path $widgetDir 'Start-Widget.ps1') -BackendPort $BackendPort -FrontendPort $FrontendPort | Out-Null
            $widgetUp = Wait-Until -Condition { @(Get-RunningWidget -WidgetDir $widgetDir).Count -gt 0 } -TimeoutSeconds $StartupTimeoutSeconds
            $widgetState = if ($widgetUp) { 'running' } else { 'failed' }
            if ($widgetUp) { $widgetPid = @(Get-RunningWidget -WidgetDir $widgetDir)[0].ProcessId }
        } catch {
            Write-Host "ERROR: the widget did not start: $($_.Exception.Message)"
            $widgetState = 'failed'
        }
    }
}

Save-RunState

Write-Host "Waiting for the frontend..."
$frontendUp = Wait-Until -Condition { Test-HttpUp -Url "http://127.0.0.1:$FrontendPort/" } -TimeoutSeconds $StartupTimeoutSeconds

Write-Host ""
$summary = @(
    [PSCustomObject]@{ Name = 'backend'; State = $(if ($backendUp) { 'running' } else { 'failed' }); Address = "http://localhost:$BackendPort" }
    [PSCustomObject]@{ Name = 'frontend'; State = $(if ($frontendUp) { 'running' } else { 'failed' }); Address = "http://localhost:$FrontendPort" }
    [PSCustomObject]@{ Name = 'widget'; State = $widgetState; Address = $null }
)
if (-not (Write-StartSummary -Result $summary)) { exit 1 }

if (-not $Remote) {
    Write-Host "Reachable from this machine only. Turn on Remote mode (dashboard or widget), or run with -Remote, for the gateway."
    exit 0
}

$backendUrl = "http://127.0.0.1:$BackendPort"

function Get-RemoteMode {
    try {
        return (Invoke-RestMethod -Uri "$backendUrl/api/meta" -TimeoutSec 3).remote_mode
    } catch {
        return $null
    }
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

Write-Host "Remote mode is ready. Open the dashboard on this machine and use 'Open on another device' to show the sign-in QR."
