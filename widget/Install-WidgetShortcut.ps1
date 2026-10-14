<#
.SYNOPSIS
Creates a desktop shortcut, and/or a logon autostart, that starts the Ledger widget.

.DESCRIPTION
Both shortcuts run Start-Widget.vbs (silent, no console window). -Desktop puts "Ledger Widget" on
the desktop for one-click startup. -Startup puts it in the current user's Startup folder, so the
widget (and the backend it needs) starts at sign-in; it shows up in Windows' Startup apps list
where it can also be switched off. Neither needs elevation. Run Uninstall-WidgetShortcut.ps1 to
remove them.

.PARAMETER Desktop
Create the desktop shortcut.

.PARAMETER Startup
Create the Startup-folder shortcut (logon autostart).

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\widget\Install-WidgetShortcut.ps1 -Desktop

.EXAMPLE
.\widget\Install-WidgetShortcut.ps1 -Desktop -Startup

.LINK
.\Uninstall-WidgetShortcut.ps1
#>

param(
    [switch]$Desktop,
    [switch]$Startup,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help -or (-not $Desktop -and -not $Startup)) {
    Get-Help $PSCommandPath -Detailed
    return
}

$launcher = Join-Path $PSScriptRoot 'Start-Widget.vbs'
$electronExe = Join-Path $PSScriptRoot 'node_modules\electron\dist\electron.exe'
$shortcutName = 'Ledger Widget.lnk'

function New-WidgetShortcut {
    param([string]$Folder)
    $path = Join-Path $Folder $shortcutName
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($path)
    $link.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
    $link.Arguments = '"' + $launcher + '"'
    $link.WorkingDirectory = $PSScriptRoot
    $link.Description = 'Start the Ledger live-sessions widget'
    if (Test-Path $electronExe) { $link.IconLocation = "$electronExe,0" }
    $link.Save()
    Write-Host "Created $path"
}

if ($Desktop) { New-WidgetShortcut -Folder ([Environment]::GetFolderPath('Desktop')) }
if ($Startup) { New-WidgetShortcut -Folder ([Environment]::GetFolderPath('Startup')) }
