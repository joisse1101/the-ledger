<#
.SYNOPSIS
Script-level checks for Start-Widget.ps1 (no Pester): -Help works, and with a backend already
answering, the widget starts without starting a second backend or a frontend, and a second run
brings no second widget.

.DESCRIPTION
Stands up a throwaway loopback server that answers /api/meta and /api/live like the backend, runs
Start-Widget.ps1 against it, and inspects the process list. Needs the widget built and its
dependencies installed (the empty node_modules case swaps the folder aside for a real reinstall).
Exits 0 when every check passes, 1 otherwise. Run from anywhere:
    powershell -File widget\tests\Test-StartWidget.ps1
#>

$ErrorActionPreference = 'Stop'
$widgetDir = Split-Path $PSScriptRoot -Parent
$startScript = Join-Path $widgetDir 'Start-Widget.ps1'
$failures = New-Object System.Collections.Generic.List[string]

function Check {
    param([bool]$Condition, [string]$Name)
    if ($Condition) { Write-Host "PASS  $Name" } else { Write-Host "FAIL  $Name"; $failures.Add($Name) }
}

function Get-WidgetMainProcesses {
    # The Electron main process (no --type= switch) whose command line points at this widget folder.
    Get-CimInstance Win32_Process -Filter "Name = 'electron.exe'" |
        Where-Object { $_.CommandLine -like "*$widgetDir*" -and $_.CommandLine -notmatch '--type=' }
}

function Get-FrontendProcesses {
    @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'vite' -and $_.CommandLine -match 'preview' })
}

function Stop-Widgets {
    # Every Electron process of this widget folder (main and children), until none holds the folder.
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        $running = @(Get-CimInstance Win32_Process -Filter "Name = 'electron.exe'" |
            Where-Object { $_.CommandLine -like "*$widgetDir*" })
        if ($running.Count -eq 0) { return }
        foreach ($proc in $running) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 1
    }
}

# 1. -Help
$help = & $startScript -Help | Out-String
Check ($help -match 'Start-Widget') '-Help prints the script help'

# 2. A backend is already up
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("widget-test-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$port = Get-Random -Minimum 20000 -Maximum 40000
$requestLog = Join-Path $tmp 'requests.log'
$stubFile = Join-Path $tmp 'stub.mjs'
@'
import http from 'node:http'
import fs from 'node:fs'
const [port, log] = [process.argv[2], process.argv[3]]
http.createServer((req, res) => {
  fs.appendFileSync(log, req.method + ' ' + req.url + '\n')
  res.setHeader('Content-Type', 'application/json')
  res.end(req.url === '/api/live' ? '{"sessions":[]}' : '{}')
}).listen(Number(port), '127.0.0.1')
'@ | Set-Content -Path $stubFile -Encoding utf8
$stub = Start-Process node -ArgumentList $stubFile, $port, $requestLog -WindowStyle Hidden -PassThru

$widget = $null
try {
    Start-Sleep -Seconds 1
    $before = @(Get-WidgetMainProcesses).Count
    Check ($before -eq 0) 'no widget is running before the test (quit it first if this fails)'

    $frontendsBefore = (Get-FrontendProcesses).Count
    $widget = & $startScript -BackendPort $port -PassThru
    Start-Sleep -Seconds 8

    $mains = @(Get-WidgetMainProcesses)
    Check ($mains.Count -eq 1) 'the widget is running'
    Check ((Test-Path $requestLog) -and ((Get-Content $requestLog) -contains 'GET /api/live')) 'the widget polls the backend that was already up'

    $backends = @(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -match 'server\.py' -and $_.CommandLine -match "--port $port\b" })
    Check ($backends.Count -eq 0) 'no second backend was started'

    Check ((Get-FrontendProcesses).Count -le $frontendsBefore) 'no frontend was started'

    # 3. A second run brings no second widget
    $second = & $startScript -BackendPort $port -PassThru
    Start-Sleep -Seconds 5
    Check (@(Get-WidgetMainProcesses).Count -eq 1) 'a second run leaves exactly one widget'
    Check ($second.HasExited) 'the second launch exits on its own'

    # 4. An empty node_modules (the folder exists, nothing in it) is repaired, then the widget starts.
    Stop-Widgets
    $modules = Join-Path $widgetDir 'node_modules'
    $aside = "$modules.test-aside"
    Rename-Item -LiteralPath $modules -NewName (Split-Path $aside -Leaf)
    New-Item -ItemType Directory -Path $modules | Out-Null
    try {
        & $startScript -BackendPort $port | Out-Null
        Start-Sleep -Seconds 8
        Check (Test-Path (Join-Path $modules 'electron\dist\electron.exe')) 'an empty node_modules is reinstalled, Electron binary included'
        Check (@(Get-WidgetMainProcesses).Count -eq 1) 'the widget starts after the repair'
    } finally {
        Stop-Widgets
        if (Test-Path (Join-Path $modules 'electron\dist\electron.exe')) {
            Remove-Item -LiteralPath $aside -Recurse -Force
        } else {
            Remove-Item -LiteralPath $modules -Recurse -Force
            Rename-Item -LiteralPath $aside -NewName 'node_modules'
        }
    }
} finally {
    foreach ($proc in @($widget, $stub)) {
        if ($proc -and -not $proc.HasExited) { & taskkill /PID $proc.Id /T /F 2>&1 | Out-Null }
    }
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
    Write-Host "`n$($failures.Count) check(s) failed."
    exit 1
}
Write-Host "`nAll checks passed."
exit 0
