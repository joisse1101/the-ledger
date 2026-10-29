<#
.SYNOPSIS
Starts the Ledger desktop widget, and with it only the backend the widget needs.

.DESCRIPTION
Resolves the ports, makes sure the widget is installed and built, then launches Electron. The widget
itself starts the backend (hidden, no console window) if nothing answers on its port, and adopts one
that is already running. It never starts the frontend or the gateway container: the tray's "Open
Ledger" starts the frontend on demand. Quitting the widget stops only the processes the widget
started. A second launch just brings the running widget forward.

Ports are the ones Start-Ledger.ps1 chose and saved (scripts\Ledger-Common.ps1 has the rules):
for the backend an explicit parameter, then the repo root's .env, then the saved port, then the
first free port in 8501-8599, which is saved. The frontend port is the explicit parameter, .env, an
already-set FRONTEND_PORT, the saved port, then 8502; it is never scanned because this script does
not start the frontend.

Before launching it checks the backend's Python environment, the widget's packages and the Electron
binary against their requirements and lock files, and installs whatever is missing or out of date
(`pip install`, `npm ci`), which needs network access. It stops with an error when that fails. It
rebuilds the widget when the sources are newer than the build.

.PARAMETER BackendPort
Port of the backend API. Default: the saved port, else the first free one in 8501-8599.

.PARAMETER FrontendPort
Port the dashboard frontend is served on when "Open Ledger" starts it. Default: the saved port, else 8502.

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

. (Join-Path $repoRoot 'scripts\Ledger-Common.ps1')

$defaultFrontendPort = 8502
$envFileValues = Read-EnvFile -Path (Join-Path $repoRoot '.env')
$savedPorts = Get-SavedPorts

$backend = Resolve-LedgerPort -Explicit $BackendPort -Name 'BACKEND_PORT' -EnvFileValues $envFileValues `
    -SavedPorts $savedPorts -ReuseWhen { param($port) Test-LedgerBackend -Port $port }
if ($backend.Source -eq 'scanned') { Save-Port -Name 'BACKEND_PORT' -Port $backend.Port }
$env:BACKEND_PORT = $backend.Port

$savedFrontend = if ($savedPorts.ContainsKey('FRONTEND_PORT')) { $savedPorts['FRONTEND_PORT'] } else { $defaultFrontendPort }
$env:FRONTEND_PORT = Resolve-Port -Explicit $FrontendPort -Name 'FRONTEND_PORT' -Default $savedFrontend -EnvFileValues $envFileValues

# The backend the widget starts needs its environment as much as the widget needs its packages.
Invoke-DependencyRepair -RepoRoot $repoRoot -Component 'api', 'widget'

Push-Location $widgetDir
try {
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

$electronExe = Get-ElectronPath -RepoRoot $repoRoot
$process = Start-Process -FilePath $electronExe -ArgumentList ('"' + $widgetDir + '"') -WorkingDirectory $widgetDir -PassThru
if ($PassThru) { $process }
