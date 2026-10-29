<#
.SYNOPSIS
Shared helpers for the Ledger start and install scripts. Dot-source it; it runs nothing on its own.

.DESCRIPTION
One copy of the logic Start-Ledger.ps1, Install-Ledger.ps1, widget\Start-Widget.ps1 and
hooks\Install-ClaudeHooks.ps1 all need: the repo root's .env parser, port resolution, the
prerequisite check and the stamp comparison the dependency repair is built on. Every function takes
its inputs as parameters (paths, hashtables, a command resolver) so the tests can drive it without
touching real user state.

    . (Join-Path $PSScriptRoot 'scripts\Ledger-Common.ps1')
#>

# Official download pages printed when a prerequisite is missing.
$script:LedgerPrerequisites = @(
    [PSCustomObject]@{ Name = 'Python'; Command = 'python'; Url = 'https://www.python.org/downloads/'; RemoteOnly = $false }
    [PSCustomObject]@{ Name = 'Node';   Command = 'node';   Url = 'https://nodejs.org/en/download';   RemoteOnly = $false }
    [PSCustomObject]@{ Name = 'Docker'; Command = 'docker'; Url = 'https://www.docker.com/products/docker-desktop/'; RemoteOnly = $true }
)

function Read-EnvFile {
    # KEY=value lines of a .env file as a hashtable; comments, blanks and a missing file give nothing.
    param([string]$Path)
    $values = @{}
    if (-not (Test-Path $Path)) { return $values }
    foreach ($line in Get-Content $Path) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$' -and $line -notmatch '^\s*#') {
            $values[$Matches[1]] = $Matches[2]
        }
    }
    return $values
}

function Resolve-Port {
    # Highest wins: explicit parameter, the repo .env, an already-set environment variable, the default.
    param(
        [int]$Explicit,
        [string]$Name,
        [int]$Default,
        [hashtable]$EnvFileValues = @{}
    )
    if ($Explicit) { return $Explicit }
    if ($EnvFileValues.ContainsKey($Name)) { return [int]$EnvFileValues[$Name] }
    $existing = [Environment]::GetEnvironmentVariable($Name)
    if ($existing) { return [int]$existing }
    return $Default
}

function Get-MissingPrerequisites {
    # The prerequisites that cannot be found. Docker counts only with -Remote. -Resolver maps a
    # command name to $true/$false so a test can pretend a tool is absent.
    param(
        [switch]$Remote,
        [scriptblock]$Resolver = { param($command) [bool](Get-Command $command -ErrorAction SilentlyContinue) }
    )
    $script:LedgerPrerequisites |
        Where-Object { ($Remote -or -not $_.RemoteOnly) -and -not (& $Resolver $_.Command) }
}

function Get-FilesStamp {
    # One hash over the content of the given files, in the order given; a missing file is an error
    # for the caller to see rather than a silently shorter stamp.
    param([string[]]$Path)
    $hashes = foreach ($file in $Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash }
    $bytes = [Text.Encoding]::UTF8.GetBytes(($hashes -join ':'))
    return ([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($bytes)) -replace '-', '')
}

function Test-Stamp {
    # True when the stamp file exists and records exactly this value.
    param([string]$StampPath, [string]$Value)
    if (-not (Test-Path $StampPath)) { return $false }
    return ((Get-Content $StampPath -Raw).Trim() -eq $Value)
}

function Write-Stamp {
    param([string]$StampPath, [string]$Value)
    Set-Content -Path $StampPath -Value $Value -Encoding ascii
}
