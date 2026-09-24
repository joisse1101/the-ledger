<#
.SYNOPSIS
Stops and removes the gateway container (the counterpart to Start-Gateway.ps1).

.DESCRIPTION
Doesn't touch the backend or frontend - those are separate local processes started/stopped on
their own.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Stop-Gateway.ps1
#>
param(
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

Push-Location $PSScriptRoot
try {
    docker compose down
} finally {
    Pop-Location
}
