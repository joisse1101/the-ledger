<#
.SYNOPSIS
Prints a toolkit item's content hash and its metadata.version / metadata.last_updated as JSON.

.DESCRIPTION
An item is a skill folder, a command namespace folder, or a single .md file (a rule, an agent or a
command). The hash covers every file's relative path and content in a stable order, so two copies of
an item have the same hash exactly when they are identical. Install-Toolkit.ps1 dot-sources this
file for the same functions, so a hash recorded in a review matches the installer's view of the item.

Version and date come from the `metadata:` map in each .md file's frontmatter (the skill's SKILL.md,
or every .md file of a command namespace). When several files differ, versions are listed
comma-separated and the latest date is shown. Both are null when no file declares them.

.PARAMETER ItemPath
The skill folder, command folder or .md file to describe.

.EXAMPLE
.\Get-ItemHash.ps1 -ItemPath ~\.claude\rules\python.md
{ "item": "python.md", "hash": "3F-...", "version": "1.0.0", "last_updated": "2026-10-14" }

.EXAMPLE
. .\Get-ItemHash.ps1
Get-ItemHash C:\path\to\rule.md      # dot-sourced: defines the functions and prints nothing
#>

# The parameter name is unlikely on purpose: dot-sourcing binds it in the caller's scope.
param([string]$ItemPath)

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

function Get-FileMetadata([string]$File) {
    # The flat string map under `metadata:` in the frontmatter, or an empty table.
    $text = [System.IO.File]::ReadAllText($File).Replace("`r`n", "`n")
    $result = @{}
    if ($text -notmatch '(?s)\A---\n(.*?)\n---') { return $result }
    $front = $Matches[1] + "`n"
    if ($front -notmatch '(?m)^metadata:[ \t]*\n((?:[ \t]+\S[^\n]*\n)+)') { return $result }
    foreach ($pair in [regex]::Matches($Matches[1], '(?m)^[ \t]+([\w-]+):[ \t]*(.*?)[ \t]*$')) {
        $result[$pair.Groups[1].Value] = $pair.Groups[2].Value.Trim('"', "'")
    }
    return $result
}

function Get-ItemVersion([string]$Item) {
    # Version and last_updated of an item, or $null when none of its files declares a version.
    $entry = Get-Item -LiteralPath $Item
    if (-not $entry.PSIsContainer) { $files = @($entry) }
    elseif (Test-Path -LiteralPath (Join-Path $entry.FullName 'SKILL.md')) { $files = @(Get-Item -LiteralPath (Join-Path $entry.FullName 'SKILL.md')) }
    else { $files = @(Get-ChildItem -LiteralPath $entry.FullName -File -Filter *.md) }

    $versions = [System.Collections.Generic.List[string]]::new()
    $dates = [System.Collections.Generic.List[string]]::new()
    foreach ($file in $files) {
        $meta = Get-FileMetadata $file.FullName
        if ($meta.ContainsKey('version') -and -not $versions.Contains($meta['version'])) { $versions.Add($meta['version']) }
        if ($meta.ContainsKey('last_updated')) { $dates.Add($meta['last_updated']) }
    }
    if ($versions.Count -eq 0) { return $null }
    $versions.Sort()
    $dates.Sort()
    return [pscustomobject]@{
        Version     = $versions -join ', '
        LastUpdated = if ($dates.Count -gt 0) { $dates[$dates.Count - 1] } else { $null }
    }
}

# Run directly (not dot-sourced): describe the item. Strict mode is set only here so that
# dot-sourcing leaves the caller's settings alone.
if ($MyInvocation.InvocationName -ne '.') {
    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'
    if (-not $ItemPath) { throw 'Usage: Get-ItemHash.ps1 -ItemPath <skill folder | command folder | .md file>' }
    $version = Get-ItemVersion $ItemPath
    [ordered]@{
        item         = (Get-Item -LiteralPath $ItemPath).Name
        hash         = Get-ItemHash $ItemPath
        version      = if ($version) { $version.Version } else { $null }
        last_updated = if ($version) { $version.LastUpdated } else { $null }
    } | ConvertTo-Json
}
