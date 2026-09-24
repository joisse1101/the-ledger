<#
.SYNOPSIS
Starts the whole Ledger app from one place: backend, frontend and (optionally) the LAN gateway.

.DESCRIPTION
Starts all three pieces of the app: the backend (`python server.py`), the frontend (a `vite` dev
server, or a `vite build` + `vite preview`, per -Mode), and the gateway container (unless
-NoGateway) - each still the same separate process/container CLAUDE.md's "Setup & Run" describes,
just launched together. Backend and frontend each open in their own window so their logs and Ctrl+C
stay independent; the gateway is a container, so it's started inline (`docker compose up -d
--build`) and this script then prints its sign-in link/QR the same way gateway\Start-Gateway.ps1
does. The backend/frontend window PIDs are recorded to the root .ledger-run.json (gitignored) so the
paired Stop-Ledger.ps1 can stop exactly these two windows (and their child processes) without
touching any other window you have open.

-Mode picks how the backend and frontend run - it has no effect on the gateway, which always starts
the same way either way. `build` (the default, matching normal local use) runs `npm run build` once
and then serves the built app via `vite preview`, which doesn't rebuild on save, and starts the
backend without `--reload`. `dev` runs `vite`'s hot-reloading dev server instead, and starts the
backend with uvicorn's `--reload` (restarts on saved changes under `api/`) - for actively working on
either side. `--reload` re-imports server.py fresh per restart, so the backend's own startup
banner/token print (see server.py's `main()`) is only ever accurate for the first start of a
`-Mode dev` session.

Port precedence per BackendPort/FrontendPort/GatewayPort (highest wins): an explicit -*Port
parameter, then the repo root's .env (see .env.example), then an already-set
BACKEND_PORT/FRONTEND_PORT/GATEWAY_PORT environment variable, then the hardcoded defaults (8501,
4173, 8080) - the same precedence gateway\Start-Gateway.ps1 uses.

The gateway needs Docker Desktop; -NoGateway skips it entirely, leaving the app reachable from this
machine only (see CLAUDE.md's "From another device on your network").

.PARAMETER Mode
'build' (default): build the frontend once and serve it with `vite preview`; backend without
--reload. 'dev': hot-reloading vite dev server; backend with --reload.

.PARAMETER NoGateway
Skip the gateway container (this machine only).

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
Build mode: backend + frontend + gateway.

.EXAMPLE
.\Start-Ledger.ps1 -Mode dev
Backend and frontend as hot-reloading dev servers.

.EXAMPLE
.\Start-Ledger.ps1 -NoGateway
Skip the gateway container.

.EXAMPLE
.\Start-Ledger.ps1 -BackendPort 9000 -FrontendPort 5000 -GatewayPort 9090
Override every port.

.LINK
.\Stop-Ledger.ps1 stops everything this script started.
#>

param(
    [ValidateSet('dev', 'build')]
    [string]$Mode = 'build',
    [switch]$NoGateway,
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

Write-Host "Starting backend on port $BackendPort in $Mode mode (new window)..."
$backendReloadFlag = if ($Mode -eq 'dev') { ' --reload' } else { '' }
$backendCommand = "Set-Location '$PSScriptRoot\api'; & '$python' server.py --port $BackendPort --frontend-port $FrontendPort$backendReloadFlag"
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

if ($NoGateway) {
    Write-Host "Skipping the gateway (-NoGateway) - reachable from this machine only."
    exit 0
}

Write-Host "Starting gateway on port $GatewayPort..."
$env:GATEWAY_PORT = $GatewayPort
$env:BACKEND_PORT = $BackendPort
$env:FRONTEND_PORT = $FrontendPort

Push-Location (Join-Path $PSScriptRoot 'gateway')
try {
    docker compose up -d --build
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Gateway failed to start (is Docker Desktop running?) - backend and frontend are still up in their own windows."
    exit 1
}

# The backend just started in its own window above and needs a moment to provision its access
# token before gateway_signin.py (which only reads it, never provisions it) has anything to read.
$tokenFile = Join-Path $PSScriptRoot 'api\.ledger\token'
$waited = 0
while (-not (Test-Path $tokenFile) -and $waited -lt 30) {
    Start-Sleep -Seconds 1
    $waited++
}

& $python (Join-Path $PSScriptRoot 'api\gateway_signin.py') --gateway-port $GatewayPort
exit $LASTEXITCODE
