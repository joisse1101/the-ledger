<#
Stops and removes the gateway container (the counterpart to Start-Gateway.ps1).

Doesn't touch the backend or frontend - those are separate local processes
started/stopped on their own.

Usage: .\Stop-Gateway.ps1
#>

$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    docker compose down
} finally {
    Pop-Location
}
