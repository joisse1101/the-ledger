<#
.SYNOPSIS
Registers the Windows Scheduled Task that runs backup_history.py daily.

.DESCRIPTION
Creates the same Task Scheduler entry CLAUDE.md's "Setup & Run" section describes doing by hand:
`api\.venv\Scripts\pythonw.exe backup_history.py` (the windowless Python, so no console flashes;
`python.exe` with a printed warning if `pythonw.exe` is missing), "Start in" `api\`, run as the logged-in user with
no elevation ("Run only when user is logged on", RunLevel Limited), on a daily trigger - so
`api/.history/history.db` (see CLAUDE.md's "Data layer" section) keeps accumulating even when this
app isn't running. Safe to re-run: an existing task with the same -TaskName is updated in place
(action/trigger/settings only) rather than duplicated.

Called directly from `hooks\ledgerScripts\`. .\Uninstall-HistoryBackupTask.ps1, alongside this
script, removes what this one creates (also wired into the root Stop-Ledger.ps1 via
-UninstallBackupTask).

.PARAMETER TaskName
Name of the Scheduled Task. Default 'Ledger History Backup'.

.PARAMETER Time
Daily trigger time, 24h `HH:mm`. Default '14:00'.

.PARAMETER ScriptsDir
Test only. Replaces the folder that holds python.exe and pythonw.exe (default: api\.venv\Scripts).

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Install-HistoryBackupTask.ps1
Create (or update) the daily backup task at 14:00.

.EXAMPLE
.\Install-HistoryBackupTask.ps1 -Time 23:30
Create/update it with a different daily trigger time.

.LINK
.\Uninstall-HistoryBackupTask.ps1 removes what this script creates.

.LINK
CLAUDE.md's "Setup & Run" section - "Keeping session history past Claude Code's own retention
window" - documents the equivalent manual steps and how to verify the task ran.
#>

param(
    [string]$TaskName = 'Ledger History Backup',
    [string]$Time = '14:00',
    [string]$ScriptsDir,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$apiDir = Join-Path $repoRoot 'api'
if (-not $ScriptsDir) { $ScriptsDir = Join-Path $apiDir '.venv\Scripts' }
$consolePython = Join-Path $ScriptsDir 'python.exe'
if (-not (Test-Path $consolePython)) {
    throw "No venv python found at $consolePython - create it first (see CLAUDE.md's Setup & Run)."
}
# pythonw.exe has no console, so the task opens no window. Its runs are recorded in backup.log
# beside history.db instead (see backup_history.py).
$pythonExe = Join-Path $ScriptsDir 'pythonw.exe'
if (-not (Test-Path $pythonExe)) {
    Write-Warning "pythonw.exe not found at $pythonExe - the task will use python.exe, which may flash a console window."
    $pythonExe = $consolePython
}

$triggerTime = [datetime]::ParseExact($Time, 'HH:mm', $null)
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument 'backup_history.py' -WorkingDirectory $apiDir
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Set-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings | Out-Null
    Write-Host "Updated existing scheduled task '$TaskName' - daily at $Time, running $pythonExe backup_history.py (Start in $apiDir)."
} else {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
    Write-Host "Created scheduled task '$TaskName' - daily at $Time, running $pythonExe backup_history.py (Start in $apiDir)."
}

Write-Host "Trigger it once now to verify: Start-ScheduledTask -TaskName '$TaskName'"
