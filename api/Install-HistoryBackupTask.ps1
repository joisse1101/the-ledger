<#
.SYNOPSIS
Registers (or removes) the Windows Scheduled Task that runs backup_history.py daily.

.DESCRIPTION
Creates the same Task Scheduler entry CLAUDE.md's "Setup & Run" section describes doing by hand:
`api\.venv\Scripts\python.exe backup_history.py`, "Start in" `api\`, run as the logged-in user with
no elevation ("Run only when user is logged on", RunLevel Limited), on a daily trigger - so
`api/.history/history.db` (see CLAUDE.md's "Data layer" section) keeps accumulating even when this
app isn't running. Safe to re-run: an existing task with the same -TaskName is updated in place
(action/trigger/settings only) rather than duplicated.

Called directly from `api\`, or via the root Start-Ledger.ps1's -InstallBackupTask switch.

.PARAMETER TaskName
Name of the Scheduled Task. Default 'Ledger History Backup'.

.PARAMETER Time
Daily trigger time, 24h `HH:mm`. Default '02:00'.

.PARAMETER Uninstall
Remove the task instead of creating/updating it.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Install-HistoryBackupTask.ps1
Create (or update) the daily backup task at 02:00.

.EXAMPLE
.\Install-HistoryBackupTask.ps1 -Time 23:30
Create/update it with a different daily trigger time.

.EXAMPLE
.\Install-HistoryBackupTask.ps1 -Uninstall
Remove the task.

.LINK
CLAUDE.md's "Setup & Run" section - "Keeping session history past Claude Code's own retention
window" - documents the equivalent manual steps and how to verify the task ran.
#>

param(
    [string]$TaskName = 'Ledger History Backup',
    [string]$Time = '02:00',
    [switch]$Uninstall,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed scheduled task '$TaskName'."
    } else {
        Write-Host "No scheduled task named '$TaskName' exists - nothing to remove."
    }
    return
}

$apiDir = $PSScriptRoot
$pythonExe = Join-Path $apiDir '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    throw "No venv python found at $pythonExe - create it first (see CLAUDE.md's Setup & Run)."
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
