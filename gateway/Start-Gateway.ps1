<#
.SYNOPSIS
Starts the gateway container.

.DESCRIPTION
Starts the gateway container (building it if needed). It does not sign devices in: the access token
exists only while Remote mode is on, so turn Remote mode on from the dashboard (or run
Start-Ledger.ps1 -Remote) and scan the QR shown there. Without Remote mode, every request from
another device is refused.

Precedence per port (highest wins): an explicit -GatewayPort/-BackendPort/-FrontendPort, then the
repo root's .env (see .env.example) - so that file is the one place to look/set these regardless of
whatever's already in your shell - then an already-set GATEWAY_PORT/BACKEND_PORT/FRONTEND_PORT
environment variable, then the hardcoded defaults (8503, 8501, 8502).

.PARAMETER GatewayPort
Port the gateway is published on. Default 8503. Avoid Chromium's restricted ports (e.g. 10080).

.PARAMETER BackendPort
Port of the running backend the gateway proxies /api/ to. Default 8501.

.PARAMETER FrontendPort
Port of the running frontend the gateway proxies / to. Default 8502.

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

$GatewayPort = Resolve-Port -Explicit $GatewayPort -Name 'GATEWAY_PORT' -Default 8503
$BackendPort = Resolve-Port -Explicit $BackendPort -Name 'BACKEND_PORT' -Default 8501
$FrontendPort = Resolve-Port -Explicit $FrontendPort -Name 'FRONTEND_PORT' -Default 8502

$env:GATEWAY_PORT = $GatewayPort
$env:BACKEND_PORT = $BackendPort
$env:FRONTEND_PORT = $FrontendPort

Push-Location $PSScriptRoot
try {
    docker compose up -d --build
} finally {
    Pop-Location
}
