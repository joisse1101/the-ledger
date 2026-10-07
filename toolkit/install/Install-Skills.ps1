<#
.SYNOPSIS
Copies the toolkit's skills, agents and commands into an AI tool's folders (Claude Code by default).

.DESCRIPTION
The toolkit holds three kinds of item:
  skills    toolkit\skills\<name>\      a folder containing SKILL.md
  agents    toolkit\agents\<name>.md    one file per subagent
  commands  toolkit\commands\<name>.md  one file per slash command
This script copies them - one named item, or all of them - into the tool's global folders (e.g.
~/.claude/skills, ~/.claude/agents, ~/.claude/commands) or into a project's (<project>\.claude\...).
Where each tool reads each kind from lives in targets.json next to this script, so supporting another
tool or kind is a new entry there, not new code.

A destination item that already exists and differs from the toolkit's copy is never overwritten
silently: it is reported as "differs" and skipped unless -Force is given. "Differs" is decided by a
SHA-256 over every file's relative path and content. -List shows that state per item without changing
anything. -Uninstall removes only items that exist in the toolkit; any other skill, agent or command
in the destination is left alone. Nothing outside those three folders is touched (settings.json and
hooks included).

Copy the files by hand instead if you prefer - see toolkit\README.md.

.PARAMETER Scope
'global' (default) or 'project'.

.PARAMETER Path
The project folder. Required with -Scope project.

.PARAMETER Kind
Restrict the action to 'skills', 'agents' or 'commands'. Omit to act on every kind.

.PARAMETER Name
Name of one item to act on (for a kind, the folder or file name without .md). Omit to act on all.
If the name exists under several kinds, every match is acted on unless -Kind narrows it.

.PARAMETER Skill
Same as -Name with -Kind skills. Kept for compatibility.

.PARAMETER Target
Which tool's entry in targets.json to use. Default 'claude-code'.

.PARAMETER List
Show each toolkit item's state at the destination (missing / up to date / differs) and exit.

.PARAMETER Uninstall
Remove the toolkit's items (or just the named one) from the destination.

.PARAMETER Force
Overwrite a destination item that differs from the toolkit's copy.

.PARAMETER Help
Show this help and exit (-h works too).

.EXAMPLE
.\Install-Skills.ps1
Install every toolkit skill, agent and command globally.

.EXAMPLE
.\Install-Skills.ps1 -Scope project -Path C:\code\my-app -Kind agents
Install only the agents into a project.

.EXAMPLE
.\Install-Skills.ps1 -Name code-audit -List
Show whether the code-audit skill and command are installed globally and whether they have drifted.
#>

[CmdletBinding()]
param(
    [ValidateSet('global', 'project')]
    [string]$Scope = 'global',
    [string]$Path,
    [ValidateSet('skills', 'agents', 'commands')]
    [string]$Kind,
    [string]$Name,
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

if ($Skill) {
    if ($Name -and $Name -ne $Skill) { throw "-Skill and -Name disagree; use -Name." }
    if ($Kind -and $Kind -ne 'skills') { throw "-Skill means a skill; it conflicts with -Kind $Kind." }
    $Name = $Skill
    $Kind = 'skills'
}

$toolkitRoot = Split-Path $PSScriptRoot -Parent
$allKinds = @('skills', 'agents', 'commands')

function Get-ItemHash([string]$Item) {
    # Hashes a folder (every file's relative path + content) or a single file (its name + content).
    # Get-Item's FullName is the same form Get-ChildItem reports below (Resolve-Path can keep 8.3
    # short names, which would throw off the relative-path substring).
    $info = Get-Item -LiteralPath $Item
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        if ($info.PSIsContainer) {
            $root = $info.FullName.TrimEnd('\')
            $files = Get-ChildItem -LiteralPath $root -Recurse -File |
                Sort-Object { $_.FullName.Substring($root.Length + 1).Replace('\', '/') } |
                ForEach-Object { [pscustomobject]@{ Rel = $_.FullName.Substring($root.Length + 1).Replace('\', '/'); Full = $_.FullName } }
        }
        else {
            $files = @([pscustomobject]@{ Rel = $info.Name; Full = $info.FullName })
        }
        foreach ($f in $files) {
            $relBytes = [System.Text.Encoding]::UTF8.GetBytes($f.Rel + "`n")
            [void]$sha.TransformBlock($relBytes, 0, $relBytes.Length, $null, 0)
            $content = [System.IO.File]::ReadAllBytes($f.Full)
            [void]$sha.TransformBlock($content, 0, $content.Length, $null, 0)
        }
        [void]$sha.TransformFinalBlock([byte[]]::new(0), 0, 0)
        return [System.BitConverter]::ToString($sha.Hash)
    }
    finally { $sha.Dispose() }
}

function Get-AvailableItems([string]$ItemKind) {
    # skills: every folder under toolkit\skills holding a SKILL.md.
    # agents / commands: every .md file directly under toolkit\agents / toolkit\commands.
    $dir = Join-Path $toolkitRoot $ItemKind
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) { return @() }
    if ($ItemKind -eq 'skills') {
        Get-ChildItem -LiteralPath $dir -Directory |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
            ForEach-Object { [pscustomobject]@{ Kind = $ItemKind; Name = $_.Name; Source = $_.FullName; Leaf = $_.Name } }
    }
    else {
        Get-ChildItem -LiteralPath $dir -File -Filter '*.md' |
            ForEach-Object { [pscustomobject]@{ Kind = $ItemKind; Name = $_.BaseName; Source = $_.FullName; Leaf = $_.Name } }
    }
}

function Get-ItemState($Item, [string]$DestRoot) {
    $dest = Join-Path $DestRoot $Item.Leaf
    if (-not (Test-Path -LiteralPath $dest)) { return 'missing' }
    if ((Get-ItemHash $Item.Source) -eq (Get-ItemHash $dest)) { return 'up to date' }
    return 'differs'
}

# Items to act on, narrowed by -Kind and -Name.
$kinds = if ($Kind) { @($Kind) } else { $allKinds }
$available = @(foreach ($k in $kinds) { Get-AvailableItems $k })

if ($Name) {
    $items = @($available | Where-Object { $_.Name -eq $Name })
    if ($items.Count -eq 0) {
        $names = ($available | ForEach-Object { "$($_.Kind)/$($_.Name)" }) -join ', '
        throw "Unknown item '$Name'. Available items: $names"
    }
}
else {
    $items = $available
}

# Destination roots, from targets.json.
$targets = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'targets.json') -Raw | ConvertFrom-Json
$entry = $targets.$Target
if (-not $entry) {
    $known = ($targets.PSObject.Properties.Name) -join ', '
    throw "Unknown target '$Target'. Known targets: $known"
}

if ($Scope -eq 'project') {
    if (-not $Path) { throw "-Scope project needs -Path <project folder>." }
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Project folder not found: $Path" }
    $projectRoot = (Resolve-Path -LiteralPath $Path).Path
}

function Get-DestRoot([string]$ItemKind) {
    $kindEntry = $entry.$ItemKind
    if (-not $kindEntry) { throw "Target '$Target' has no '$ItemKind' destination in targets.json." }
    if ($Scope -eq 'global') {
        $rel = [string]$kindEntry.global
        if ($rel.StartsWith('~')) { $rel = Join-Path $HOME $rel.Substring(1).TrimStart('/', '\') }
        return $rel
    }
    return Join-Path $projectRoot ([string]$kindEntry.project)
}

# Wizard: run with no flags and every choice is a numbered menu. Flags still work for scripting.
$wizard = $PSBoundParameters.Count -eq 0 -and [Environment]::UserInteractive

function Read-Menu([string]$Title, [string[]]$Options) {
    Write-Host "`n$Title" -ForegroundColor Cyan
    for ($i = 0; $i -lt $Options.Count; $i++) { Write-Host ("  {0}. {1}" -f ($i + 1), $Options[$i]) }
    while ($true) {
        $a = (Read-Host 'Choose a number').Trim()
        if ($a -match '^\d+$' -and [int]$a -ge 1 -and [int]$a -le $Options.Count) { return [int]$a - 1 }
    }
}

function Read-YesNo([string]$Question) { (Read-Host "$Question [y/N]").Trim() -like 'y*' }

if ($wizard) {
    $mode = Read-Menu 'What do you want to do?' @('Install', 'Check what is installed', 'Uninstall')
    $List = $mode -eq 1
    $Uninstall = $mode -eq 2

    if ((Read-Menu 'Where?' @('Globally, for every project (~/.claude)', 'In one project (<project>/.claude)')) -eq 1) {
        $Scope = 'project'
        do { $p = (Read-Host 'Project folder').Trim('" ') } until ($p -and (Test-Path -LiteralPath $p -PathType Container))
        $projectRoot = (Resolve-Path -LiteralPath $p).Path
    }

    $labels = @()
    foreach ($it in $available) {
        $labels += ("{0,-9} {1,-16} {2}" -f $it.Kind, $it.Name, (Get-ItemState $it (Get-DestRoot $it.Kind)))
    }
    Write-Host "`nToolkit items:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $labels.Count; $i++) { Write-Host ("  {0}. {1}" -f ($i + 1), $labels[$i]) }
    Write-Host '  (/code-audit needs the skill, both agents and the command.)'
    $ans = (Read-Host 'Which? Numbers like 1,3  |  all  |  Enter for all').Trim().ToLowerInvariant()
    if ($ans -and $ans -ne 'all') {
        $nums = $ans -split '[,\s]+' | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ }
        $items = @($nums | Sort-Object -Unique | Where-Object { $_ -ge 1 -and $_ -le $available.Count } | ForEach-Object { $available[$_ - 1] })
        if (-not $items) { Write-Host 'No valid choice; nothing to do.'; return }
    }

    if (-not $List -and -not $Uninstall) {
        $differing = @($items | Where-Object { (Get-ItemState $_ (Get-DestRoot $_.Kind)) -eq 'differs' })
        if ($differing) {
            Write-Host "`nThese differ from the toolkit's copy: $(($differing | ForEach-Object { $_.Name }) -join ', ')"
            $Force = Read-YesNo 'Overwrite them with the toolkit version?'
        }
    }
    elseif ($Uninstall -and -not (Read-YesNo "`nRemove $($items.Count) toolkit item(s) from the destination?")) {
        Write-Host 'Cancelled.'; return
    }
    Write-Host ''
}

Write-Host "Target: $Target ($Scope)"

foreach ($group in ($items | Group-Object Kind)) {
    $destRoot = Get-DestRoot $group.Name
    Write-Host "[$($group.Name)] -> $destRoot"

    if ($List) {
        foreach ($item in $group.Group) {
            Write-Host ("  {0,-30} {1}" -f $item.Name, (Get-ItemState $item $destRoot))
        }
        continue
    }

    if ($Uninstall) {
        foreach ($item in $group.Group) {
            $dest = Join-Path $destRoot $item.Leaf
            if (Test-Path -LiteralPath $dest) {
                Remove-Item -LiteralPath $dest -Recurse -Force
                Write-Host "  removed     $($item.Name)"
            }
            else {
                Write-Host "  not present $($item.Name)"
            }
        }
        continue
    }

    New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
    foreach ($item in $group.Group) {
        $dest = Join-Path $destRoot $item.Leaf
        switch (Get-ItemState $item $destRoot) {
            'up to date' { Write-Host "  up to date  $($item.Name)" }
            'differs' {
                if ($Force) {
                    Remove-Item -LiteralPath $dest -Recurse -Force
                    Copy-Item -LiteralPath $item.Source -Destination $dest -Recurse
                    Write-Host "  overwritten $($item.Name)"
                }
                else {
                    Write-Host "  differs     $($item.Name) (left unchanged; re-run with -Force to overwrite)"
                }
            }
            'missing' {
                Copy-Item -LiteralPath $item.Source -Destination $dest -Recurse
                Write-Host "  installed   $($item.Name)"
            }
        }
    }
}

if ($wizard -and -not $List -and -not $Uninstall -and (Read-YesNo "`nSet up the optional scanners /code-audit can use (gitleaks, ruff, eslint, ...)?")) {
    & (Join-Path $PSScriptRoot 'Install-Scanners.ps1')
}

if ($wizard) {
    Write-Host "`nTo verify:" -ForegroundColor Cyan
    Write-Host '  .\Install-Skills.ps1 -List      each item should say "up to date"'
    Write-Host '  .\Install-Scanners.ps1          each scanner shows "ok: <version>" if it really runs'
    Write-Host 'Then start a NEW Claude Code session and run /code-audit; tools that cannot run are listed as skipped.'
}
