<#
.SYNOPSIS
Copies the toolkit's skills, slash commands and rules into an AI tool's folders (Claude Code by default).

.DESCRIPTION
Each folder under toolkit\skills\ is one skill. Each entry directly under toolkit\commands\ is one
command item: a folder (a namespace such as opsx\, giving /opsx:apply) or a single .md file (giving
/name). Each .md file directly under toolkit\rules\ is one rule (optionally with paths: frontmatter
limiting it to matching files). This script copies them - one named item, or all of them - into the
tool's global folders (e.g. ~/.claude/skills, ~/.claude/commands and ~/.claude/rules) or into a
project's (<project>\.claude\...). Where each
tool reads them from lives in targets.json next to this script, so supporting another tool is a new
entry there, not new code.

A destination item that already exists and differs from the toolkit's copy is never overwritten
silently: it is reported as "differs" and skipped unless -Force is given. "Differs" is decided by a
hash over every file's relative path and content. -List shows that state per item without changing
anything. -Uninstall removes only items that exist in the toolkit; anything else in the destination is
left alone. Nothing outside the skills, commands and rules folders is touched (settings.json and hooks
included).

Copy by hand instead if you prefer - see toolkit\README.md.

.PARAMETER Scope
'global' (default) or 'project'.

.PARAMETER Path
The project folder. Required with -Scope project.

.PARAMETER Skill
Name of one skill to act on. With -Skill, -Command and/or -Rule, only the named items are acted on.

.PARAMETER Command
Name of one command item to act on: a folder name (opsx) or a file name (review.md).

.PARAMETER Rule
Name of one rule to act on: a file name (java.md).

.PARAMETER Target
Which tool's entry in targets.json to use. Default 'claude-code'.

.PARAMETER List
Show each toolkit item's state at the destination (missing / up to date / differs) and exit.

.PARAMETER Uninstall
Remove the toolkit's items (or just the named ones) from the destination.

.PARAMETER Force
Overwrite a destination item that differs from the toolkit's copy.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Install-Toolkit.ps1
Install every toolkit skill, command and rule globally.

.EXAMPLE
.\Install-Toolkit.ps1 -Scope project -Path C:\code\my-app -Skill coding-standards -Command opsx
Install one skill and one command namespace into a project.

.EXAMPLE
.\Install-Toolkit.ps1 -List
Show what is installed globally and whether it has drifted.
#>

[CmdletBinding()]
param(
    [ValidateSet('global', 'project')]
    [string]$Scope = 'global',
    [string]$Path,
    [string]$Skill,
    [string]$Command,
    [string]$Rule,
    [string]$Target = 'claude-code',
    [switch]$List,
    [switch]$Uninstall,
    [switch]$Force,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    return
}

$toolkitRoot = Split-Path $PSScriptRoot -Parent

function Get-ItemHash([string]$Item) {
    # A skill or command namespace is a folder; a single command is one file. Both hash the same
    # way: every file's relative path and content, in a stable order. Get-Item's FullName is the
    # same form Get-ChildItem reports below (Resolve-Path can keep 8.3 short names, which would
    # throw off the relative-path substring).
    $entry = Get-Item -LiteralPath $Item
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        if ($entry.PSIsContainer) {
            $root = $entry.FullName.TrimEnd('\')
            $files = Get-ChildItem -LiteralPath $root -Recurse -File |
                Sort-Object { $_.FullName.Substring($root.Length + 1).Replace('\', '/') }
            $pairs = [System.Collections.Generic.List[object]]::new()
            foreach ($f in $files) { $pairs.Add(@($f.FullName.Substring($root.Length + 1).Replace('\', '/'), $f.FullName)) }
        }
        else {
            $pairs = [System.Collections.Generic.List[object]]::new()
            $pairs.Add(@($entry.Name, $entry.FullName))
        }
        foreach ($pair in $pairs) {
            $relBytes = [System.Text.Encoding]::UTF8.GetBytes($pair[0] + "`n")
            [void]$sha.TransformBlock($relBytes, 0, $relBytes.Length, $null, 0)
            $content = [System.IO.File]::ReadAllBytes($pair[1])
            [void]$sha.TransformBlock($content, 0, $content.Length, $null, 0)
        }
        [void]$sha.TransformFinalBlock([byte[]]::new(0), 0, 0)
        return [System.BitConverter]::ToString($sha.Hash)
    }
    finally { $sha.Dispose() }
}

function Get-ItemState($Item) {
    if (-not (Test-Path -LiteralPath $Item.Dest)) { return 'missing' }
    if ((Get-ItemHash $Item.Source) -eq (Get-ItemHash $Item.Dest)) { return 'up to date' }
    return 'differs'
}

# Available items per kind. A skill is a folder holding a SKILL.md; a command item is any folder or
# .md file directly under toolkit\commands.
$skillsRoot = Join-Path $toolkitRoot 'skills'
$commandsRoot = Join-Path $toolkitRoot 'commands'
$rulesRoot = Join-Path $toolkitRoot 'rules'
$availableSkills = @()
if (Test-Path -LiteralPath $skillsRoot) {
    $availableSkills = @(Get-ChildItem -LiteralPath $skillsRoot -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
        ForEach-Object Name)
}
$availableCommands = @()
if (Test-Path -LiteralPath $commandsRoot) {
    $availableCommands = @(Get-ChildItem -LiteralPath $commandsRoot |
        Where-Object { $_.PSIsContainer -or $_.Extension -eq '.md' } |
        ForEach-Object Name)
}
$availableRules = @()
if (Test-Path -LiteralPath $rulesRoot) {
    $availableRules = @(Get-ChildItem -LiteralPath $rulesRoot -File -Filter *.md | ForEach-Object Name)
}

if ($Skill -and $availableSkills -notcontains $Skill) {
    throw "Unknown skill '$Skill'. Available skills: $($availableSkills -join ', ')"
}
if ($Command -and $availableCommands -notcontains $Command) {
    throw "Unknown command '$Command'. Available commands: $($availableCommands -join ', ')"
}
if ($Rule -and $availableRules -notcontains $Rule) {
    throw "Unknown rule '$Rule'. Available rules: $($availableRules -join ', ')"
}

if ($Skill -or $Command -or $Rule) {
    $skillNames = @(if ($Skill) { $Skill })
    $commandNames = @(if ($Command) { $Command })
    $ruleNames = @(if ($Rule) { $Rule })
}
else {
    $skillNames = $availableSkills
    $commandNames = $availableCommands
    $ruleNames = $availableRules
}

# Destinations, from targets.json.
$targets = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'targets.json') -Raw | ConvertFrom-Json
$entry = $targets.$Target
if (-not $entry) {
    $known = ($targets.PSObject.Properties.Name) -join ', '
    throw "Unknown target '$Target'. Known targets: $known"
}

function Resolve-DestRoot([string]$Kind) {
    $setting = $entry.$Kind
    if (-not $setting) { throw "Target '$Target' has no '$Kind' entry in targets.json." }
    if ($Scope -eq 'global') {
        $rel = [string]$setting.global
        if ($rel.StartsWith('~')) { $rel = Join-Path $HOME $rel.Substring(1).TrimStart('/', '\') }
        return $rel
    }
    if (-not $Path) { throw "-Scope project needs -Path <project folder>." }
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Project folder not found: $Path" }
    return Join-Path (Resolve-Path -LiteralPath $Path).Path ([string]$setting.project)
}

$items = @()
if ($skillNames.Count -gt 0) {
    $destRoot = Resolve-DestRoot 'skills'
    $items += $skillNames | ForEach-Object {
        [pscustomobject]@{ Kind = 'skill'; Name = $_; Source = Join-Path $skillsRoot $_; Dest = Join-Path $destRoot $_; DestRoot = $destRoot }
    }
}
if ($commandNames.Count -gt 0) {
    $destRoot = Resolve-DestRoot 'commands'
    $items += $commandNames | ForEach-Object {
        [pscustomobject]@{ Kind = 'command'; Name = $_; Source = Join-Path $commandsRoot $_; Dest = Join-Path $destRoot $_; DestRoot = $destRoot }
    }
}
if ($ruleNames.Count -gt 0) {
    $destRoot = Resolve-DestRoot 'rules'
    $items += $ruleNames | ForEach-Object {
        [pscustomobject]@{ Kind = 'rule'; Name = $_; Source = Join-Path $rulesRoot $_; Dest = Join-Path $destRoot $_; DestRoot = $destRoot }
    }
}

Write-Host "Target: $Target ($Scope)"
foreach ($root in ($items | ForEach-Object DestRoot | Select-Object -Unique)) { Write-Host "  -> $root" }

if ($List) {
    foreach ($item in $items) {
        Write-Host ("  {0,-8} {1,-30} {2}" -f $item.Kind, $item.Name, (Get-ItemState $item))
    }
    return
}

if ($Uninstall) {
    foreach ($item in $items) {
        if (Test-Path -LiteralPath $item.Dest) {
            Remove-Item -LiteralPath $item.Dest -Recurse -Force
            Write-Host ("  removed     {0} {1}" -f $item.Kind, $item.Name)
        }
        else {
            Write-Host ("  not present {0} {1}" -f $item.Kind, $item.Name)
        }
    }
    return
}

foreach ($item in $items) {
    $label = '{0} {1}' -f $item.Kind, $item.Name
    switch (Get-ItemState $item) {
        'up to date' { Write-Host "  up to date  $label" }
        'differs' {
            if ($Force) {
                Remove-Item -LiteralPath $item.Dest -Recurse -Force
                Copy-Item -LiteralPath $item.Source -Destination $item.Dest -Recurse
                Write-Host "  overwritten $label"
            }
            else {
                Write-Host "  differs     $label (left unchanged; re-run with -Force to overwrite)"
            }
        }
        'missing' {
            New-Item -ItemType Directory -Force -Path $item.DestRoot | Out-Null
            Copy-Item -LiteralPath $item.Source -Destination $item.Dest -Recurse
            Write-Host "  installed   $label"
        }
    }
}
