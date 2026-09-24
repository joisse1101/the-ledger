<#
.SYNOPSIS
Reverses Install-ClaudeHooks.ps1: removes the toast hooks and, optionally, the Ledger relay hook.

.DESCRIPTION
By default this removes the Notification/Stop hook entries referencing Send-ClaudeToast.ps1 from
settings.json, removes the claudecode:// protocol handler, and deletes the files that Install put
in %USERPROFILE%\.claude\hooks (only the files listed in .\scripts, in case that folder holds
other, unrelated hook scripts too).

With -IncludeSessionControl it also removes the optional Ledger relay hook: the PreToolUse entry
referencing Relay-PreToolUse.ps1 (other PreToolUse hooks are left alone) and the installed
ledgerScripts folder.

.PARAMETER IncludeSessionControl
Also remove the optional Ledger relay hook (PreToolUse).

.PARAMETER SkipToastHooks
Leave the toast hooks alone: don't touch the Notification/Stop hooks, the claudecode:// handler, or
the toast scripts. Combine with -IncludeSessionControl to remove only the relay hook. Does nothing
on its own.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Uninstall-ClaudeHooks.ps1
Removes the toast hooks only.

.EXAMPLE
.\Uninstall-ClaudeHooks.ps1 -IncludeSessionControl
Removes the toast hooks and the relay hook.

.EXAMPLE
.\Uninstall-ClaudeHooks.ps1 -IncludeSessionControl -SkipToastHooks
Removes only the relay hook, leaving the toast hooks installed.
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

if ($SkipToastHooks -and -not $IncludeSessionControl) {
    Write-Host 'Nothing to uninstall: -SkipToastHooks without -IncludeSessionControl.'
    return
}

$hooksDir = Join-Path $env:USERPROFILE '.claude\hooks'
$ledgerScriptsDir = Join-Path $hooksDir 'ledgerScripts'
$settingsPath = Join-Path $env:USERPROFILE '.claude\settings.json'

# 1. Remove the hook entries from settings.json
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    if ($settings.PSObject.Properties['hooks']) {
        if (-not $SkipToastHooks) {
            foreach ($eventName in 'Notification', 'Stop') {
                if ($settings.hooks.PSObject.Properties[$eventName]) {
                    $kept = @($settings.hooks.$eventName) | Where-Object {
                        -not (@($_.hooks) | Where-Object { $_.command -like '*Send-ClaudeToast.ps1*' })
                    }
                    $settings.hooks.$eventName = @($kept)
                }
            }
            Write-Host "Removed toast hooks from $settingsPath"
        }
        if ($IncludeSessionControl -and $settings.hooks.PSObject.Properties['PreToolUse']) {
            $kept = @(@($settings.hooks.PreToolUse) | Where-Object {
                -not (@($_.hooks) | Where-Object { $_.command -like '*Relay-PreToolUse.ps1*' })
            })
            if ($kept.Count -gt 0) {
                $settings.hooks.PreToolUse = $kept
            } else {
                $settings.hooks.PSObject.Properties.Remove('PreToolUse')
            }
            Write-Host "Removed the PreToolUse relay hook from $settingsPath"
        }
        $settings | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsPath -Encoding utf8
    }
} else {
    Write-Host "$settingsPath not found, skipping"
}

if (-not $SkipToastHooks) {
    # 2. Remove the claudecode:// protocol handler
    if (Test-Path 'HKCU:\Software\Classes\claudecode') {
        Remove-Item -Path 'HKCU:\Software\Classes\claudecode' -Recurse -Force
        Write-Host 'Removed the claudecode:// protocol handler'
    } else {
        Write-Host 'claudecode:// protocol handler not registered, skipping'
    }

    # 3. Delete just the installed files (not the whole folder, in case other
    #    unrelated hook scripts live there too)
    foreach ($file in Get-ChildItem -Path (Join-Path $PSScriptRoot 'scripts') -File) {
        $path = Join-Path $hooksDir $file.Name
        if (Test-Path $path) {
            Remove-Item -Path $path -Force
        }
    }
    Write-Host "Removed the hook scripts from $hooksDir"
}

# 4. Delete the relay hook's own folder (it only ever holds what Install copied there)
if ($IncludeSessionControl) {
    if (Test-Path $ledgerScriptsDir) {
        Remove-Item -Path $ledgerScriptsDir -Recurse -Force
        Write-Host "Removed the session-control scripts from $ledgerScriptsDir"
    } else {
        Write-Host "$ledgerScriptsDir not found, skipping"
    }
}

if ((Test-Path $hooksDir) -and -not (Get-ChildItem -Path $hooksDir -Force)) {
    Remove-Item -Path $hooksDir -Force
    Write-Host "$hooksDir was empty, removed it too"
}

Write-Host "`nDone."
