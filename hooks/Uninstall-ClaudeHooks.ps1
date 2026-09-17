<#
Reverses Install-ClaudeHooks.ps1: removes the Notification/Stop hook entries
referencing Send-ClaudeToast.ps1 from settings.json, removes the
claudecode:// protocol handler, and deletes the files that Install put there
(only the files listed in .\scripts, in case %USERPROFILE%\.claude\hooks
holds other, unrelated hook scripts too).
#>

$ErrorActionPreference = 'Stop'

$hooksDir = Join-Path $env:USERPROFILE '.claude\hooks'
$settingsPath = Join-Path $env:USERPROFILE '.claude\settings.json'

# 1. Remove the hook entries from settings.json
if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    if ($settings.PSObject.Properties['hooks']) {
        foreach ($eventName in 'Notification', 'Stop') {
            if ($settings.hooks.PSObject.Properties[$eventName]) {
                $kept = @($settings.hooks.$eventName) | Where-Object {
                    -not (@($_.hooks) | Where-Object { $_.command -like '*Send-ClaudeToast.ps1*' })
                }
                $settings.hooks.$eventName = @($kept)
            }
        }
        $settings | ConvertTo-Json -Depth 10 | Set-Content -Path $settingsPath -Encoding utf8
        Write-Host "Removed toast hooks from $settingsPath"
    }
} else {
    Write-Host "$settingsPath not found, skipping"
}

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

if ((Test-Path $hooksDir) -and -not (Get-ChildItem -Path $hooksDir -Force)) {
    Remove-Item -Path $hooksDir -Force
    Write-Host "$hooksDir was empty, removed it too"
}

Write-Host "`nDone."
