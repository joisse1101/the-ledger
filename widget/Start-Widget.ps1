<#
.SYNOPSIS
Starts the Ledger desktop widget, and with it only the backend the widget needs.

.DESCRIPTION
Resolves the ports, makes sure the widget is installed and built, then launches Electron. The widget
itself starts the backend (hidden, no console window) if nothing answers on its port, and adopts one
that is already running. It never starts the frontend or the gateway container: the tray's "Open
Ledger" starts the frontend on demand. Quitting the widget stops only the processes the widget
started. A second launch just brings the running widget forward.

Port precedence per BackendPort/FrontendPort (highest wins): an explicit parameter, then the repo
root's .env, then an already-set BACKEND_PORT/FRONTEND_PORT environment variable, then the defaults
(8501, 4173) - the same precedence Start-Ledger.ps1 uses.

On the first run it installs the widget's dependencies (`npm ci`), which needs network access once.
It rebuilds the widget when the sources are newer than the build.

.PARAMETER BackendPort
Port of the backend API. Default 8501.

.PARAMETER FrontendPort
Port the dashboard frontend is served on when "Open Ledger" starts it. Default 4173.

.PARAMETER PassThru
Return the launched Electron process (used by the tests).

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\widget\Start-Widget.ps1

.LINK
.\Install-WidgetShortcut.ps1 creates the desktop shortcut and the optional logon autostart.
#>

param(
    [int]$BackendPort,
    [int]$FrontendPort,
    [switch]$PassThru,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

$widgetDir = $PSScriptRoot
$repoRoot = Split-Path $widgetDir -Parent

$envFileValues = @{}
$rootEnvFile = Join-Path $repoRoot '.env'
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

$env:BACKEND_PORT = Resolve-Port -Explicit $BackendPort -Name 'BACKEND_PORT' -Default 8501
$env:FRONTEND_PORT = Resolve-Port -Explicit $FrontendPort -Name 'FRONTEND_PORT' -Default 4173

Push-Location $widgetDir
try {
    if (-not (Test-Path (Join-Path $widgetDir 'node_modules'))) {
        Write-Host 'Installing the widget dependencies (first run only)...'
        npm ci
        if ($LASTEXITCODE -ne 0) {
            throw 'npm ci failed. The widget needs network access once to install; nothing was started.'
        }
    }

    $electronExe = Join-Path $widgetDir 'node_modules\electron\dist\electron.exe'
    if (-not (Test-Path $electronExe)) {
        # Electron fetches its binary in a post-install step that can be skipped; run it now.
        node (Join-Path $widgetDir 'node_modules\electron\install.js')
        if (-not (Test-Path $electronExe)) {
            throw 'The Electron binary is missing and could not be downloaded; nothing was started.'
        }
    }

    $built = Join-Path $widgetDir 'dist\main\index.js'
    $newestSource = Get-ChildItem (Join-Path $widgetDir 'src') -Recurse -File |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not (Test-Path $built) -or (Get-Item $built).LastWriteTime -lt $newestSource.LastWriteTime) {
        Write-Host 'Building the widget...'
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'The widget build failed; nothing was started.' }
    }
} finally {
    Pop-Location
}

$process = Start-Process -FilePath $electronExe -ArgumentList ('"' + $widgetDir + '"') -WorkingDirectory $widgetDir -PassThru
if ($PassThru) { $process }
