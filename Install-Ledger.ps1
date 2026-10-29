<#
.SYNOPSIS
Sets up the Ledger's optional extras on this machine, explaining each before it changes anything.

.DESCRIPTION
Run once after cloning (and again whenever you want to change what is installed). It offers, one at
a time: the desktop widget shortcut (and, separately, starting it at sign-in), the toast hooks, the
relay hook and the daily history backup task. Before each question it says what the extra does, what
it changes on the machine and what declining means. It installs only what you accept, then prints
what it did.

It first checks that Python and Node are installed and stops with the download pages if not. Then it
asks every question, then installs what was accepted, so you can stop (Ctrl+C) before anything changes.
Accepting the shortcut also installs the widget's packages (and the backend's environment) first, so
the shortcut's first launch, which shows no window while it prepares, is not slow or silently broken.
If the relay hook is already installed, you are offered a reinstall instead of a first install: that
updates the backend port it uses.

Each extra is installed by its own script (widget\Install-WidgetShortcut.ps1,
hooks\Install-ClaudeHooks.ps1, hooks\ledgerScripts\Install-HistoryBackupTask.ps1), which asks nothing
itself. Running this again is safe: shortcuts, hook entries and the scheduled task are updated in
place, never duplicated.

With no console to ask on (a scheduled or piped run), an extra that is not pre-answered is skipped.
Pre-answer with the per-extra switches below, or -Yes for all of them.

.PARAMETER Shortcut
'ask' (default), 'yes' or 'no': the desktop shortcut that starts the widget and the backend it needs.

.PARAMETER Autostart
'ask' (default), 'yes' or 'no': also start the widget at sign-in. Only offered with the shortcut.

.PARAMETER ToastHooks
'ask' (default), 'yes' or 'no': the Windows toast notifications for Claude Code.

.PARAMETER RelayHook
'ask' (default), 'yes' or 'no': answer a session's blocking prompts from the dashboard.

.PARAMETER BackupTask
'ask' (default), 'yes' or 'no': the daily history backup scheduled task.

.PARAMETER Yes
Answer yes to every extra that was not pre-answered.

.PARAMETER BackendPort
Backend port to bake into the relay hook. Default: chosen the way Start-Ledger.ps1 chooses it (.env,
then the saved port, then the first free one in 8501-8599).

.PARAMETER DesktopPath
Folder for the desktop shortcut. Default: your Desktop. The tests point it at a throwaway folder.

.PARAMETER StartupPath
Folder for the sign-in shortcut. Default: your Startup folder. The tests point it at a throwaway
folder.

.PARAMETER TaskName
Name of the backup scheduled task. Default 'Ledger History Backup'. The tests use a throwaway name.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Install-Ledger.ps1
Walk through each extra and answer as you go.

.EXAMPLE
.\Install-Ledger.ps1 -Shortcut yes -Autostart no -ToastHooks no -RelayHook no -BackupTask yes
Unattended: the shortcut and the backup task only.

.LINK
.\Start-Ledger.ps1 starts the app; .\Stop-Ledger.ps1 stops it.
#>

param(
    [ValidateSet('ask', 'yes', 'no')][string]$Shortcut = 'ask',
    [ValidateSet('ask', 'yes', 'no')][string]$Autostart = 'ask',
    [ValidateSet('ask', 'yes', 'no')][string]$ToastHooks = 'ask',
    [ValidateSet('ask', 'yes', 'no')][string]$RelayHook = 'ask',
    [ValidateSet('ask', 'yes', 'no')][string]$BackupTask = 'ask',
    [switch]$Yes,
    [int]$BackendPort,
    [string]$DesktopPath,
    [string]$StartupPath,
    [string]$TaskName = 'Ledger History Backup',
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

. (Join-Path $PSScriptRoot 'scripts\Ledger-Common.ps1')

if (-not (Test-Prerequisites)) { exit 1 }

function Get-Mode {
    param([string]$Mode)
    if ($Yes -and $Mode -eq 'ask') { return 'yes' }
    return $Mode
}

function Read-ExtraChoice {
    # Says what the extra does, changes and means to decline, then asks (or applies the pre-answer).
    param([string]$Title, [string]$Does, [string]$Changes, [string]$Declining, [string]$Mode, [string]$Question)
    Write-Host ""
    Write-Host "== $Title"
    Write-Host "What it does:    $Does"
    Write-Host "What it changes: $Changes"
    Write-Host "If you decline:  $Declining"
    return (Resolve-InstallChoice -Mode (Get-Mode $Mode) -Question $Question)
}

$wantShortcut = Read-ExtraChoice -Title 'Widget shortcut' -Mode $Shortcut -Question 'Create the Ledger Widget desktop shortcut?' `
    -Does 'Puts a "Ledger Widget" shortcut on your Desktop that starts the always-on-top live-sessions widget and the backend it needs, with no console window.' `
    -Changes 'Creates "Ledger Widget.lnk" on your Desktop.' `
    -Declining 'No shortcut. You can still start the widget with widget\Start-Widget.ps1, or everything with Start-Ledger.ps1.'

$wantAutostart = $false
if ($wantShortcut) {
    $wantAutostart = Read-ExtraChoice -Title 'Start the widget at sign-in' -Mode $Autostart -Question 'Start the widget when you sign in?' `
        -Does 'Starts the widget, and the backend it needs, each time you sign in to Windows.' `
        -Changes 'Creates "Ledger Widget.lnk" in your Startup folder; it appears in Windows'' Startup apps list, where you can also switch it off.' `
        -Declining 'Nothing starts at sign-in. The desktop shortcut keeps working.'
}

$wantToast = Read-ExtraChoice -Title 'Toast hooks' -Mode $ToastHooks -Question 'Install the Claude Code toast hooks?' `
    -Does 'Shows a Windows toast when a Claude Code session needs input or finishes; clicking it focuses that repo''s VS Code window. Needs the BurntToast PowerShell module.' `
    -Changes 'Copies the toast scripts into %USERPROFILE%\.claude\hooks, registers the claudecode:// protocol handler for your user, and edits %USERPROFILE%\.claude\settings.json to add Notification and Stop hooks.' `
    -Declining 'No toasts, and your Claude Code settings are left alone.'

$installedRelayPort = Get-RelayHookPort
$relayChanges = 'Copies the relay script into %USERPROFILE%\.claude\hooks\ledgerScripts and adds a PermissionRequest hook to %USERPROFILE%\.claude\settings.json with the backend port baked in.'
if ($null -eq $installedRelayPort) {
    $wantRelay = Read-ExtraChoice -Title 'Relay hook' -Mode $RelayHook -Question 'Install the Ledger relay hook?' `
        -Does 'Lets you answer a live session''s permission prompts and questions from the Ledger dashboard, on this PC or another device. The terminal dialog keeps working either way.' `
        -Changes $relayChanges `
        -Declining 'Prompts can only be answered in the terminal, and your Claude Code settings are left alone.'
} else {
    $wantRelay = Read-ExtraChoice -Title 'Relay hook (already installed)' -Mode $RelayHook -Question 'Reinstall the Ledger relay hook?' `
        -Does "The relay hook is installed for backend port $installedRelayPort. Reinstalling updates the backend port it uses to the one Ledger uses now, and refreshes its scripts." `
        -Changes "Rewrites the relay script and its PermissionRequest entry in %USERPROFILE%\.claude\settings.json (the entry is updated in place, not added again)." `
        -Declining "The hook stays on port $installedRelayPort; if the backend runs on another port, dashboard answers won't reach your sessions."
}

$wantBackup = Read-ExtraChoice -Title 'History backup task' -Mode $BackupTask -Question 'Register the daily history backup task?' `
    -Does 'Runs api\backup_history.py every day at 14:00 so the session history database keeps growing even when the app is not running.' `
    -Changes "Registers a Task Scheduler task named '$TaskName' that runs as you, without elevation." `
    -Declining 'History only grows while the app runs. Stop-Ledger.ps1 -UninstallBackupTask removes the task later.'

# The shortcut starts the widget hidden, so its dependencies are installed now, where failures show.
# The backup task runs the backend's venv python.
$components = @()
if ($wantShortcut) { $components += 'api', 'widget' }
if ($wantBackup) { $components += 'api' }
$components = @($components | Select-Object -Unique)
if ($components.Count -gt 0) {
    Write-Host ""
    Write-Host "Checking dependencies ($($components -join ', '))..."
    try {
        Invoke-DependencyRepair -RepoRoot $PSScriptRoot -Component $components
    } catch {
        Write-Host "ERROR: $($_.Exception.Message)"
        Write-Host "Nothing was installed."
        exit 1
    }
}

$results = New-Object System.Collections.Generic.List[object]

function Install-Extra {
    # Runs one extra's install script; a failure is recorded and the others still run.
    param([string]$Name, [bool]$Wanted, [scriptblock]$Install, [string]$DoneState = 'installed')
    if (-not $Wanted) {
        $results.Add([PSCustomObject]@{ Name = $Name; State = 'skipped' })
        return
    }
    Write-Host ""
    Write-Host "Installing: $Name"
    try {
        & $Install | Out-Host
        $results.Add([PSCustomObject]@{ Name = $Name; State = $DoneState })
    } catch {
        Write-Host "ERROR: $Name failed: $($_.Exception.Message)"
        $results.Add([PSCustomObject]@{ Name = $Name; State = 'failed' })
    }
}

$relayArgs = @{}
if ($BackendPort) { $relayArgs['BackendPort'] = $BackendPort }

$shortcutArgs = @{}
if ($DesktopPath) { $shortcutArgs['DesktopPath'] = $DesktopPath }
if ($StartupPath) { $shortcutArgs['StartupPath'] = $StartupPath }

Install-Extra -Name 'widget shortcut' -Wanted $wantShortcut -Install {
    & (Join-Path $PSScriptRoot 'widget\Install-WidgetShortcut.ps1') -Desktop @shortcutArgs
}
Install-Extra -Name 'sign-in autostart' -Wanted $wantAutostart -Install {
    & (Join-Path $PSScriptRoot 'widget\Install-WidgetShortcut.ps1') -Startup @shortcutArgs
}
Install-Extra -Name 'toast hooks' -Wanted $wantToast -Install {
    & (Join-Path $PSScriptRoot 'hooks\Install-ClaudeHooks.ps1')
}
$relayDoneState = if ($null -eq $installedRelayPort) { 'installed' } else { 'reinstalled' }
Install-Extra -Name 'relay hook' -Wanted $wantRelay -DoneState $relayDoneState -Install {
    & (Join-Path $PSScriptRoot 'hooks\Install-ClaudeHooks.ps1') -IncludeSessionControl -SkipToastHooks @relayArgs
}
Install-Extra -Name 'history backup task' -Wanted $wantBackup -Install {
    & (Join-Path $PSScriptRoot 'hooks\ledgerScripts\Install-HistoryBackupTask.ps1') -TaskName $TaskName
}

Write-Host ""
Write-Host "Summary"
foreach ($result in $results) { Write-Host ('  {0,-20} {1}' -f $result.Name, $result.State) }
if (@($results | Where-Object State -eq 'failed').Count -gt 0) { exit 1 }
Write-Host "Done. Start the app with .\Start-Ledger.ps1."
