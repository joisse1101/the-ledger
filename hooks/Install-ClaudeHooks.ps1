<#
.SYNOPSIS
Installs the Claude Code hooks for the current user: the toast notifications, and optionally the
Ledger relay hook.

.DESCRIPTION
By default this installs the toast-notification hooks: it copies everything in .\scripts into
%USERPROFILE%\.claude\hooks, registers the claudecode:// protocol handler, and merges the
Notification/Stop hooks into %USERPROFILE%\.claude\settings.json.

With -IncludeSessionControl it also installs the optional Ledger relay hook, which lets you approve
or deny a live session's tool calls from the Ledger dashboard on another device. It copies
.\ledgerScripts to %USERPROFILE%\.claude\hooks\ledgerScripts and registers a PreToolUse hook for it
(matcher Bash|Edit|MultiEdit|Write|WebFetch, timeout 130s). If nobody is watching that session in the
dashboard, the hook stays silent and Claude Code behaves exactly as if it weren't installed.

Run this directly (in your own PowerShell prompt) rather than embedding $env:USERPROFILE inside a
hook's "command" string in settings.json - Claude Code runs those via Git Bash or PowerShell
depending on the machine, and the two disagree on environment-variable syntax. This script resolves
$env:USERPROFILE once, up front, in a known shell, and writes the fully resolved literal path into
settings.json, so nothing needs to be expanded later when the hook actually fires.

Safe to re-run: copying is idempotent, and the settings.json merge updates hook entries that are
already there instead of duplicating them.

.PARAMETER IncludeSessionControl
Also install the optional Ledger relay hook (PreToolUse).

.PARAMETER SkipToastHooks
Leave the toast hooks alone: don't copy the toast scripts, register the claudecode:// handler, or
touch the Notification/Stop hooks. Combine with -IncludeSessionControl to install only the relay
hook. Does nothing on its own.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Install-ClaudeHooks.ps1
Installs the toast hooks only.

.EXAMPLE
.\Install-ClaudeHooks.ps1 -IncludeSessionControl
Installs the toast hooks and the relay hook.

.EXAMPLE
.\Install-ClaudeHooks.ps1 -IncludeSessionControl -SkipToastHooks
Installs only the relay hook.
#>
param(
    [switch]$IncludeSessionControl,
    [switch]$SkipToastHooks,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

# Curated tools that commonly need permission; a broader matcher would spawn PowerShell before every
# tool call. Editable by hand in settings.json afterwards.
$relayMatcher = 'Bash|Edit|MultiEdit|Write|WebFetch'
# Seconds. Must stay above Relay-PreToolUse.ps1's own wait (-TimeoutSeconds, default 125) or Claude
# Code kills the hook mid-wait.
$relayHookTimeout = 130

if ($SkipToastHooks -and -not $IncludeSessionControl) {
    Write-Host 'Nothing to install: -SkipToastHooks without -IncludeSessionControl.'
    return
}

$hooksDir = Join-Path $env:USERPROFILE '.claude\hooks'
$toastScript = Join-Path $hooksDir 'Send-ClaudeToast.ps1'
$ledgerScriptsDir = Join-Path $hooksDir 'ledgerScripts'
$relayScript = Join-Path $ledgerScriptsDir 'Relay-PreToolUse.ps1'
$settingsPath = Join-Path $env:USERPROFILE '.claude\settings.json'

if (-not $SkipToastHooks) {
    # 1. Copy the scripts
    New-Item -ItemType Directory -Force -Path $hooksDir | Out-Null
    Copy-Item -Path (Join-Path $PSScriptRoot 'scripts\*') -Destination $hooksDir -Force
    Write-Host "Copied scripts to $hooksDir"

    # 2. Register the claudecode:// protocol handler (HKCU, no admin needed)
    $vbsPath = Join-Path $hooksDir 'Open-ClaudeRepoWindow.vbs'
    $command = "wscript.exe `"$vbsPath`" `"%1`""

    New-Item -Path 'HKCU:\Software\Classes\claudecode' -Force | Out-Null
    Set-ItemProperty -Path 'HKCU:\Software\Classes\claudecode' -Name '(Default)' -Value 'URL:Claude Code Repo Protocol'
    Set-ItemProperty -Path 'HKCU:\Software\Classes\claudecode' -Name 'URL Protocol' -Value ''

    New-Item -Path 'HKCU:\Software\Classes\claudecode\shell\open\command' -Force | Out-Null
    Set-ItemProperty -Path 'HKCU:\Software\Classes\claudecode\shell\open\command' -Name '(Default)' -Value $command
    Write-Host 'Registered the claudecode:// protocol handler'
}

# 3. Merge the hooks into settings.json
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
} else {
    $settings = [PSCustomObject]@{}
}
if (-not $settings.PSObject.Properties['hooks']) {
    $settings | Add-Member -NotePropertyName 'hooks' -NotePropertyValue ([PSCustomObject]@{})
}

function Add-ToastHook {
    param($Settings, [string]$EventName, [string]$Title, [string]$BodyTemplate, [string]$ScriptPath)

    $command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -Title `"$Title`" -BodyTemplate `"$BodyTemplate`""

    if (-not $Settings.hooks.PSObject.Properties[$EventName]) {
        $Settings.hooks | Add-Member -NotePropertyName $EventName -NotePropertyValue @()
    }

    $alreadyInstalled = @($Settings.hooks.$EventName) | Where-Object {
        @($_.hooks) | Where-Object { $_.command -like '*Send-ClaudeToast.ps1*' -and $_.command -like "*$Title*" }
    }
    if ($alreadyInstalled) {
        Write-Host "$EventName hook for `"$Title`" already present, updating path"
        $alreadyInstalled[0].hooks[0].command = $command
        return
    }

    $newEntry = [PSCustomObject]@{
        matcher = ''
        hooks   = @([PSCustomObject]@{ type = 'command'; command = $command })
    }
    $Settings.hooks.$EventName = @($Settings.hooks.$EventName) + $newEntry
    Write-Host "Added $EventName hook for `"$Title`""
}

function Add-RelayHook {
    param($Settings, [string]$ScriptPath, [string]$Matcher, [int]$Timeout)

    $command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""

    if (-not $Settings.hooks.PSObject.Properties['PreToolUse']) {
        $Settings.hooks | Add-Member -NotePropertyName 'PreToolUse' -NotePropertyValue @()
    }

    $alreadyInstalled = @($Settings.hooks.PreToolUse) | Where-Object {
        @($_.hooks) | Where-Object { $_.command -like '*Relay-PreToolUse.ps1*' }
    }
    if ($alreadyInstalled) {
        Write-Host 'PreToolUse relay hook already present, updating path and timeout'
        $alreadyInstalled[0].hooks[0].command = $command
        $alreadyInstalled[0].hooks[0].timeout = $Timeout
        return
    }

    $newEntry = [PSCustomObject]@{
        matcher = $Matcher
        hooks   = @([PSCustomObject]@{ type = 'command'; command = $command; timeout = $Timeout })
    }
    $Settings.hooks.PreToolUse = @($Settings.hooks.PreToolUse) + $newEntry
    Write-Host "Added PreToolUse relay hook (matcher: $Matcher)"
}

if (-not $SkipToastHooks) {
    Add-ToastHook -Settings $settings -EventName 'Notification' -Title 'Claude Code Alert' -BodyTemplate 'Waiting for input in {0}!' -ScriptPath $toastScript
    Add-ToastHook -Settings $settings -EventName 'Stop' -Title 'Claude Code Done' -BodyTemplate 'Finished task in {0}!' -ScriptPath $toastScript
}

if ($IncludeSessionControl) {
    New-Item -ItemType Directory -Force -Path $ledgerScriptsDir | Out-Null
    Copy-Item -Path (Join-Path $PSScriptRoot 'ledgerScripts\*') -Destination $ledgerScriptsDir -Force
    Write-Host "Copied session-control scripts to $ledgerScriptsDir"
    Add-RelayHook -Settings $settings -ScriptPath $relayScript -Matcher $relayMatcher -Timeout $relayHookTimeout
}

New-Item -ItemType Directory -Force -Path (Split-Path $settingsPath) | Out-Null
$settings | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsPath -Encoding utf8
Write-Host "Updated $settingsPath"

if ($SkipToastHooks) {
    Write-Host "`nDone. See README.md's session-control section to verify."
} else {
    Write-Host "`nDone. Run the tests in README.md to verify (BurntToast module must already be installed)."
}
