<#
.SYNOPSIS
Removes the Ledger widget's desktop shortcut and logon autostart.

.DESCRIPTION
Deletes "Ledger Widget.lnk" from the desktop and from the Startup folder, whichever exist. Removing
one never affects the other: the desktop shortcut keeps working after autostart is switched off.
Does not touch a running widget or the widget's files.

.PARAMETER Desktop
Remove only the desktop shortcut.

.PARAMETER Startup
Remove only the Startup-folder shortcut (turn logon autostart off).

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\widget\Uninstall-WidgetShortcut.ps1
Remove both.

.EXAMPLE
.\widget\Uninstall-WidgetShortcut.ps1 -Startup
Keep the desktop shortcut; stop starting at sign-in.
#>

param(
    [switch]$Desktop,
    [switch]$Startup,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

# Neither switch means both.
if (-not $Desktop -and -not $Startup) { $Desktop = $true; $Startup = $true }

$shortcutName = 'Ledger Widget.lnk'
$folders = @()
if ($Desktop) { $folders += [Environment]::GetFolderPath('Desktop') }
if ($Startup) { $folders += [Environment]::GetFolderPath('Startup') }

foreach ($folder in $folders) {
    $path = Join-Path $folder $shortcutName
    if (Test-Path $path) {
        Remove-Item $path
        Write-Host "Removed $path"
    } else {
        Write-Host "Not present: $path"
    }
}
