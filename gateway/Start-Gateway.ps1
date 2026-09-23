<#
Starts the gateway container (building it if needed) and then prints the sign-in
link/QR for every device on this network, via api\gateway_signin.py.

The backend (`python server.py`) must already be running so a token exists to print
- if it isn't, gateway_signin.py says so and this script's exit code reflects that.

Usage: .\Start-Gateway.ps1 [-GatewayPort <port>]
#>

param(
    [int]$GatewayPort = $(if ($env:GATEWAY_PORT) { [int]$env:GATEWAY_PORT } else { 10080 })
)

$ErrorActionPreference = 'Stop'
$env:GATEWAY_PORT = $GatewayPort

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
