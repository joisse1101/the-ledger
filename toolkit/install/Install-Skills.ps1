<#
.SYNOPSIS
Copies the toolkit's skills into an AI tool's skills folder (Claude Code by default).

.DESCRIPTION
Each folder under toolkit\skills\ is one skill. This script copies them - one named skill, or all of
them - into the tool's global skills folder (e.g. ~/.claude/skills) or into a project's
(<project>\.claude\skills). Where each tool reads skills from lives in targets.json next to this
script, so supporting another tool is a new entry there, not new code.

A destination skill that already exists and differs from the toolkit's copy is never overwritten
silently: it is reported as "differs" and skipped unless -Force is given. "Differs" is decided by a
hash over every file's relative path and content. -List shows that state per skill without changing
anything. -Uninstall removes only skills that exist in the toolkit; any other skill in the destination
is left alone. Nothing outside the skills folder is touched (settings.json and hooks included).

Copy the folders by hand instead if you prefer - see toolkit\README.md.

.PARAMETER Scope
'global' (default) or 'project'.

.PARAMETER Path
The project folder. Required with -Scope project.

.PARAMETER Skill
Name of one skill to act on. Omit to act on every toolkit skill.

.PARAMETER Target
Which tool's entry in targets.json to use. Default 'claude-code'.

.PARAMETER List
Show each toolkit skill's state at the destination (missing / up to date / differs) and exit.

.PARAMETER Uninstall
Remove the toolkit's skills (or just -Skill) from the destination.

.PARAMETER Force
Overwrite a destination skill that differs from the toolkit's copy.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Install-Skills.ps1
Install every toolkit skill globally.

.EXAMPLE
.\Install-Skills.ps1 -Scope project -Path C:\code\my-app -Skill toolkit-hello
Install one skill into a project.

.EXAMPLE
.\Install-Skills.ps1 -List
Show what is installed globally and whether it has drifted.
#>

[CmdletBinding()]
param(
    [ValidateSet('global', 'project')]
    [string]$Scope = 'global',
    [string]$Path,
    [string]$Skill,
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
$sourceRoot = Join-Path $toolkitRoot 'skills'

function Get-SkillHash([string]$Dir) {
    # Get-Item's FullName is the same form Get-ChildItem reports below (Resolve-Path can keep 8.3
    # short names, which would throw off the relative-path substring).
    $root = (Get-Item -LiteralPath $Dir).FullName.TrimEnd('\')
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $files = Get-ChildItem -LiteralPath $root -Recurse -File |
            Sort-Object { $_.FullName.Substring($root.Length + 1).Replace('\', '/') }
        foreach ($f in $files) {
            $rel = $f.FullName.Substring($root.Length + 1).Replace('\', '/')
            $relBytes = [System.Text.Encoding]::UTF8.GetBytes($rel + "`n")
            [void]$sha.TransformBlock($relBytes, 0, $relBytes.Length, $null, 0)
            $content = [System.IO.File]::ReadAllBytes($f.FullName)
            [void]$sha.TransformBlock($content, 0, $content.Length, $null, 0)
        }
        [void]$sha.TransformFinalBlock([byte[]]::new(0), 0, 0)
        return [System.BitConverter]::ToString($sha.Hash)
    }
    finally { $sha.Dispose() }
}

function Get-SkillState([string]$Name, [string]$DestRoot) {
    $dest = Join-Path $DestRoot $Name
    if (-not (Test-Path -LiteralPath $dest)) { return 'missing' }
    if ((Get-SkillHash (Join-Path $sourceRoot $Name)) -eq (Get-SkillHash $dest)) { return 'up to date' }
    return 'differs'
}

# Available skills: every folder under toolkit\skills that holds a SKILL.md.
$available = @(Get-ChildItem -LiteralPath $sourceRoot -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
    ForEach-Object Name)

if ($Skill) {
    if ($available -notcontains $Skill) {
        throw "Unknown skill '$Skill'. Available skills: $($available -join ', ')"
    }
    $names = @($Skill)
}
else {
    $names = $available
}

# Destination, from targets.json.
$targets = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'targets.json') -Raw | ConvertFrom-Json
$entry = $targets.$Target
if (-not $entry) {
    $known = ($targets.PSObject.Properties.Name) -join ', '
    throw "Unknown target '$Target'. Known targets: $known"
}

if ($Scope -eq 'global') {
    $rel = [string]$entry.global
    if ($rel.StartsWith('~')) { $rel = Join-Path $HOME $rel.Substring(1).TrimStart('/', '\') }
    $destRoot = $rel
}
else {
    if (-not $Path) { throw "-Scope project needs -Path <project folder>." }
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Project folder not found: $Path" }
    $destRoot = Join-Path (Resolve-Path -LiteralPath $Path).Path ([string]$entry.project)
}

Write-Host "Target: $Target ($Scope) -> $destRoot"

if ($List) {
    foreach ($name in $names) {
        Write-Host ("  {0,-30} {1}" -f $name, (Get-SkillState $name $destRoot))
    }
    return
}

if ($Uninstall) {
    foreach ($name in $names) {
        $dest = Join-Path $destRoot $name
        if (Test-Path -LiteralPath $dest) {
            Remove-Item -LiteralPath $dest -Recurse -Force
            Write-Host "  removed     $name"
        }
        else {
            Write-Host "  not present $name"
        }
    }
    return
}

New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
foreach ($name in $names) {
    $dest = Join-Path $destRoot $name
    switch (Get-SkillState $name $destRoot) {
        'up to date' { Write-Host "  up to date  $name" }
        'differs' {
            if ($Force) {
                Remove-Item -LiteralPath $dest -Recurse -Force
                Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $dest -Recurse
                Write-Host "  overwritten $name"
            }
            else {
                Write-Host "  differs     $name (left unchanged; re-run with -Force to overwrite)"
            }
        }
        'missing' {
            Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $dest -Recurse
            Write-Host "  installed   $name"
        }
    }
}
