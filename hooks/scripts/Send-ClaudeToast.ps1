<#
Shows a BurntToast notification for a Claude Code hook event. Reads the
hook's JSON payload from stdin to get the repo path (cwd) and, when present,
the session transcript (transcript_path), from which a third "Context 394k"
line is added; that line is simply omitted if it can't be worked out. Clicking
the toast launches the claudecode:// protocol, which Open-ClaudeRepoWindow.ps1
handles by focusing (or opening) the matching VS Code window.
#>
param(
    [Parameter(Mandatory)]
    [string]$Title,

    [Parameter(Mandatory)]
    [string]$BodyTemplate  # e.g. "Finished task in {0}!"
)

# Context size = input + cache read + cache written tokens on the latest real
# main-thread assistant turn. Same rule as claude_context.py;
# if one changes, review the other. Returns $null on any problem, so the toast
# just omits the line.
function Get-ContextTokens {
    param([string]$Path)
    try {
        if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }

        # ReadWrite share: the session is still appending to this file.
        $stream = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
        try {
            $length = $stream.Length
            $window = 256KB
            while ($true) {
                $start = [Math]::Max(0, $length - $window)
                $buffer = [byte[]]::new($length - $start)
                [void]$stream.Seek($start, 'Begin')
                $filled = 0
                while ($filled -lt $buffer.Length) {
                    $read = $stream.Read($buffer, $filled, $buffer.Length - $filled)
                    if ($read -le 0) { break }
                    $filled += $read
                }
                $lines = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $filled) -split "`n"

                # A read that began mid-file starts mid-line: drop that fragment.
                $first = if ($start -gt 0) { 1 } else { 0 }
                for ($i = $lines.Length - 1; $i -ge $first; $i--) {
                    $line = $lines[$i]
                    if (-not $line.Contains('"type":"assistant"')) { continue }
                    if ($line.Contains('"isSidechain":true') -or $line.Contains('"model":"<synthetic>"')) { continue }
                    # Leading quote keeps "input_tokens" from matching inside "cache_*_input_tokens".
                    $input = [regex]::Match($line, '"input_tokens":(\d+)')
                    $cacheRead = [regex]::Match($line, '"cache_read_input_tokens":(\d+)')
                    $cacheWritten = [regex]::Match($line, '"cache_creation_input_tokens":(\d+)')
                    if (-not ($input.Success -and $cacheRead.Success -and $cacheWritten.Success)) { continue }
                    $total = [long]$input.Groups[1].Value + [long]$cacheRead.Groups[1].Value + [long]$cacheWritten.Groups[1].Value
                    if ($total -gt 0) { return $total }
                }

                if ($start -eq 0) { return $null }
                $window *= 2
            }
        } finally {
            $stream.Dispose()
        }
    } catch {
        return $null
    }
}

# 742 -> "742", 80618 -> "81k", 1234567 -> "1.2M". Same boundaries as
# claude_context.humanise_tokens.
function Format-TokenCount {
    param([long]$Count)
    if ($Count -lt 1000) { return "$Count" }
    $thousands = [long][Math]::Floor(($Count + 500) / 1000)
    if ($thousands -lt 1000) { return "${thousands}k" }
    $tenths = [long][Math]::Floor(($Count + 50000) / 100000)
    return '{0}.{1}M' -f [Math]::Floor($tenths / 10), ($tenths % 10)
}

$stdin = [Console]::In.ReadToEnd()

$cwd = $null
$transcriptPath = $null
try {
    $json = $stdin | ConvertFrom-Json
    $cwd = $json.cwd
    $transcriptPath = $json.transcript_path
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
$children = @($text1, $text2)

$contextTokens = Get-ContextTokens -Path $transcriptPath
if ($null -ne $contextTokens) {
    $children += New-BTText -Content ('Context ' + (Format-TokenCount $contextTokens))
}
$binding = New-BTBinding -Children $children
$visual = New-BTVisual -BindingGeneric $binding
$btContent = New-BTContent -Visual $visual -ActivationType Protocol -Launch $launch

Submit-BTNotification -Content $btContent
