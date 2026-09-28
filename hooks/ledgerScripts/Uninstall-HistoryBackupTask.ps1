<#
.SYNOPSIS
Reverses Install-HistoryBackupTask.ps1: removes the daily history-backup Scheduled Task.

.DESCRIPTION
Unregisters the Windows Scheduled Task Install-HistoryBackupTask.ps1 creates (default name 'Ledger
History Backup'). Does nothing but print a message if no task by that name exists - safe to run
whether or not it was ever installed.

Called directly from `hooks\ledgerScripts\`, or via the root Stop-Ledger.ps1's
-UninstallBackupTask switch.

.PARAMETER TaskName
Name of the Scheduled Task to remove. Default 'Ledger History Backup' - must match whatever
-TaskName Install-HistoryBackupTask.ps1 was given, if it was given one.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Uninstall-HistoryBackupTask.ps1
Remove the daily backup task.

.LINK
.\Install-HistoryBackupTask.ps1 creates what this script removes.
#>

param(
    [string]$TaskName = 'Ledger History Backup',
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
} else {
    Write-Host "No scheduled task named '$TaskName' exists - nothing to remove."
}
