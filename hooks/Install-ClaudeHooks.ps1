<#
Installs the Claude Code toast-notification hooks for the current user:
copies everything in .\scripts into %USERPROFILE%\.claude\hooks, registers
the claudecode:// protocol handler, and merges the Notification/Stop hooks
into %USERPROFILE%\.claude\settings.json.

Run this directly (in your own PowerShell prompt) rather than embedding
$env:USERPROFILE inside a hook's "command" string in settings.json — Claude
Code runs those via Git Bash or PowerShell depending on the machine, and the
two disagree on environment-variable syntax. Running this script resolves
$env:USERPROFILE once, up front, in a known shell, and writes the fully
resolved literal path into settings.json, so nothing needs to be expanded
later when the hook actually fires.

Safe to re-run: copying is idempotent, and the settings.json merge skips
hook entries that already reference Send-ClaudeToast.ps1 for a given title.
#>

$ErrorActionPreference = 'Stop'

$hooksDir = Join-Path $env:USERPROFILE '.claude\hooks'
$toastScript = Join-Path $hooksDir 'Send-ClaudeToast.ps1'
$settingsPath = Join-Path $env:USERPROFILE '.claude\settings.json'

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

# 3. Merge the Notification/Stop hooks into settings.json
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

Add-ToastHook -Settings $settings -EventName 'Notification' -Title 'Claude Code Alert' -BodyTemplate 'Waiting for input in {0}!' -ScriptPath $toastScript
Add-ToastHook -Settings $settings -EventName 'Stop' -Title 'Claude Code Done' -BodyTemplate 'Finished task in {0}!' -ScriptPath $toastScript

New-Item -ItemType Directory -Force -Path (Split-Path $settingsPath) | Out-Null
$settings | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsPath -Encoding utf8
Write-Host "Updated $settingsPath"

Write-Host "`nDone. Run the tests in README.md to verify (BurntToast module must already be installed)."
