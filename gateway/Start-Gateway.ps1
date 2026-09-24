<#
.SYNOPSIS
Starts the gateway container and prints the sign-in link/QR for other devices on this network.

.DESCRIPTION
Starts the gateway container (building it if needed) and then prints the sign-in link/QR for every
device on this network, via api\gateway_signin.py.

The backend (`python server.py`) must already be running so a token exists to print - if it isn't,
gateway_signin.py says so and this script's exit code reflects that.

Precedence per port (highest wins): an explicit -GatewayPort/-BackendPort/-FrontendPort, then the
repo root's .env (see .env.example) - so that file is the one place to look/set these regardless of
whatever's already in your shell - then an already-set GATEWAY_PORT/BACKEND_PORT/FRONTEND_PORT
environment variable, then the hardcoded defaults (8080, 8501, 4173).

.PARAMETER GatewayPort
Port the gateway is published on. Default 8080. Avoid Chromium's restricted ports (e.g. 10080).

.PARAMETER BackendPort
Port of the running backend the gateway proxies /api/ to. Default 8501.

.PARAMETER FrontendPort
Port of the running frontend the gateway proxies / to. Default 4173.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Start-Gateway.ps1
Start the gateway on the ports from .env (or the defaults).

.EXAMPLE
.\Start-Gateway.ps1 -GatewayPort 9090
Publish the gateway on port 9090.
#>

param(
    [int]$GatewayPort,
    [int]$BackendPort,
    [int]$FrontendPort,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

$envFileValues = @{}
$rootEnvFile = Join-Path $PSScriptRoot '..\.env'
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

$GatewayPort = Resolve-Port -Explicit $GatewayPort -Name 'GATEWAY_PORT' -Default 8080
$BackendPort = Resolve-Port -Explicit $BackendPort -Name 'BACKEND_PORT' -Default 8501
$FrontendPort = Resolve-Port -Explicit $FrontendPort -Name 'FRONTEND_PORT' -Default 4173

$env:GATEWAY_PORT = $GatewayPort
$env:BACKEND_PORT = $BackendPort
$env:FRONTEND_PORT = $FrontendPort

Push-Location $PSScriptRoot
try {
    docker compose up -d --build
} finally {
    Pop-Location
}

$venvPython = Join-Path $PSScriptRoot '..\api\.venv\Scripts\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

& $python (Join-Path $PSScriptRoot '..\api\gateway_signin.py') --gateway-port $GatewayPort
exit $LASTEXITCODE
