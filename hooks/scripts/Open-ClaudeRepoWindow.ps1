<#
.SYNOPSIS
Focuses (or opens) the VS Code window for a repo, from a claudecode:// URI.

.DESCRIPTION
Invoked by Windows when a "claudecode://open?path=<encoded repo path>" URI is activated (i.e. when
the user clicks a Claude Code toast notification). Focuses the existing VS Code window for that repo
if one is open, otherwise opens a new VS Code window for it. Also run by the Ledger API's open-repo
action.

.PARAMETER Uri
The claudecode://open?path=<url-encoded repo path> URI to open.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Open-ClaudeRepoWindow.ps1 'claudecode://open?path=C%3A%5CUsers%5Cme%5Crepo'
#>
param(
    [Parameter(Position = 0)]
    [string]$Uri,
    [switch]$Help
)

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

function Get-QueryParam {
    param([string]$Uri, [string]$Name)
    if ($Uri -match "[?&]$Name=([^&]+)") {
        return [System.Uri]::UnescapeDataString($Matches[1])
    }
    return $null
}

$path = Get-QueryParam -Uri $Uri -Name 'path'
if (-not $path -or -not (Test-Path -LiteralPath $path)) {
    exit
}

$repoName = Split-Path -Leaf $path

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;

public class ClaudeToastWinApi {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);

    public static List<KeyValuePair<IntPtr, string>> GetWindows() {
        var result = new List<KeyValuePair<IntPtr, string>>();
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            if (IsWindowVisible(hWnd)) {
                int len = GetWindowTextLength(hWnd);
                if (len > 0) {
                    var sb = new StringBuilder(len + 1);
                    GetWindowText(hWnd, sb, sb.Capacity);
                    result.Add(new KeyValuePair<IntPtr, string>(hWnd, sb.ToString()));
                }
            }
            return true;
        }, IntPtr.Zero);
        return result;
    }
}
"@

$windows = [ClaudeToastWinApi]::GetWindows()
$match = $windows |
    Where-Object { $_.Value -like "*$repoName*" -and $_.Value -like "*Visual Studio Code*" } |
    Select-Object -First 1

if ($match) {
    $hwnd = $match.Key
    if ([ClaudeToastWinApi]::IsIconic($hwnd)) {
        [ClaudeToastWinApi]::ShowWindow($hwnd, 9) # SW_RESTORE
    }
    [ClaudeToastWinApi]::SetForegroundWindow($hwnd) | Out-Null
} else {
    Start-Process -FilePath "code" -ArgumentList "`"$path`"" -NoNewWindow
}
