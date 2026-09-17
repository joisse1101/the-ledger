<#
Shows a BurntToast notification for a Claude Code hook event. Reads the
hook's JSON payload from stdin to get the repo path (cwd). Clicking the
toast launches the claudecode:// protocol, which Open-ClaudeRepoWindow.ps1
handles by focusing (or opening) the matching VS Code window.
#>
param(
    [Parameter(Mandatory)]
    [string]$Title,

    [Parameter(Mandatory)]
    [string]$BodyTemplate  # e.g. "Finished task in {0}!"
)

$stdin = [Console]::In.ReadToEnd()

$cwd = $null
try {
    $json = $stdin | ConvertFrom-Json
    $cwd = $json.cwd
} catch {
    # fall through to default below
}
if (-not $cwd) {
    $cwd = (Get-Location).Path
}

$repo = Split-Path -Leaf $cwd
$body = $BodyTemplate -f $repo
$encodedPath = [System.Uri]::EscapeDataString($cwd)
$launch = "claudecode://open?path=$encodedPath"

Import-Module BurntToast -ErrorAction SilentlyContinue

$text1 = New-BTText -Content $Title
$text2 = New-BTText -Content $body
$binding = New-BTBinding -Children $text1, $text2
$visual = New-BTVisual -BindingGeneric $binding
$btContent = New-BTContent -Visual $visual -ActivationType Protocol -Launch $launch

Submit-BTNotification -Content $btContent
