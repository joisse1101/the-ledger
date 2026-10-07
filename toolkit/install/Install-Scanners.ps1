<#
.SYNOPSIS
Menu for installing the optional scanners that /code-audit uses. No flags: just run it.

.DESCRIPTION
/code-audit runs whichever of these tools are on PATH and reports the rest as "skipped". This lists
them grouped by what they check - the Phase 0 lint and type gates per language, then the
language-independent Phase 1 scanners - numbers the ones that are not installed, and asks which to
install. Run it from inside a git repository and it also counts that repo's files per language, so you
can see whether a language is used before installing its tools.

Nothing is installed unless you pick it, and each command is printed before it runs. It installs with
winget, pipx (or pip --user) and npm, whichever is on PATH; otherwise it prints the command to run
yourself. It never touches the repo, ~/.claude or settings. Install-Skills.ps1 offers this as its
last step.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Phase 0 tools are per language; Phase 1 tools check any language. Ext = file types that make the
# tool relevant; Cmd = installer commands in order of preference (first whose program exists wins).
$tools = @(
    @{ Name = 'ruff';     Group = 'Python';          Does = 'lint + syntax gate (Phase 0)';   Exe = 'ruff';     Ext = @('.py');
       Cmd = @(@{ Prog = 'pipx'; Line = 'pipx install ruff' }, @{ Prog = 'pip'; Line = 'pip install --user ruff' }) },
    @{ Name = 'mypy';     Group = 'Python';          Does = 'type check gate (Phase 0)';      Exe = 'mypy';     Ext = @('.py');
       Cmd = @(@{ Prog = 'pipx'; Line = 'pipx install mypy' }, @{ Prog = 'pip'; Line = 'pip install --user mypy' }) },
    @{ Name = 'eslint';   Group = 'JavaScript/TypeScript'; Does = 'lint gate (Phase 0)';    Exe = 'eslint';   Ext = @('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx');
       Cmd = @(@{ Prog = 'npm'; Line = 'npm install -g eslint' }) },
    @{ Name = 'tsc';      Group = 'TypeScript';      Does = 'type check gate (Phase 0)';      Exe = 'tsc';      Ext = @('.ts', '.tsx');
       Cmd = @(@{ Prog = 'npm'; Line = 'npm install -g typescript' }) },
    @{ Name = 'clippy';   Group = 'Rust';            Does = 'lint gate (Phase 0)';            Exe = 'cargo-clippy'; Ext = @('.rs');
       Cmd = @(@{ Prog = 'rustup'; Line = 'rustup component add clippy' }) },
    @{ Name = 'gitleaks'; Group = 'Any language';    Does = 'committed secrets (Phase 1)';    Exe = 'gitleaks'; Ext = @();
       Cmd = @(@{ Prog = 'winget'; Line = 'winget install gitleaks.gitleaks' }) },
    @{ Name = 'semgrep';  Group = 'Any language';    Does = 'SAST rules (Phase 1)';           Exe = 'semgrep';  Ext = @();
       Cmd = @(@{ Prog = 'pipx'; Line = 'pipx install semgrep' }, @{ Prog = 'pip'; Line = 'pip install --user semgrep' }) },
    @{ Name = 'jscpd';    Group = 'Any language';    Does = 'duplicate code (Phase 1)';       Exe = 'jscpd';    Ext = @();
       Cmd = @(@{ Prog = 'npm'; Line = 'npm install -g jscpd' }) },
    @{ Name = 'trivy';    Group = 'Any language';    Does = 'dependency/config vulns (Phase 1)'; Exe = 'trivy'; Ext = @();
       Cmd = @(@{ Prog = 'winget'; Line = 'winget install AquaSecurity.Trivy' }) }
)


function Test-Program([string]$Prog) { [bool](Get-Command $Prog -ErrorAction SilentlyContinue) }

# The command that proves a tool actually runs, not just that its name is on PATH.
$versionCmd = @{
    ruff = 'ruff --version'; mypy = 'mypy --version'; eslint = 'eslint --version'; tsc = 'tsc --version'
    clippy = 'cargo clippy --version'; gitleaks = 'gitleaks version'; semgrep = 'semgrep --version'
    jscpd = 'jscpd --version'; trivy = 'trivy --version'
}

function Test-ToolRuns([string]$ToolName) {
    # Returns the first line of the version output, or $null if the command fails or is not found.
    try {
        # Read the exit code in the same scope that ran the command; piping it away loses it.
        $r = & ([scriptblock]::Create('$o = ' + $versionCmd[$ToolName] + ' 2>&1; [pscustomobject]@{ Code = $LASTEXITCODE; Out = @($o) }'))
        $first = @($r.Out | ForEach-Object { "$_" } | Where-Object { $_.Trim() })[0]
        if ($r.Code -eq 0 -and $first) { return $first.Trim() }
    }
    catch { }
    return $null
}

# Count tracked + untracked-not-ignored files per extension in the current git repo, if any.
$extCount = @{}
$inRepo = $false
if (Test-Program 'git') {
    $files = & git ls-files --cached --others --exclude-standard 2>$null
    if ($LASTEXITCODE -eq 0 -and $files) {
        $inRepo = $true
        foreach ($f in $files) {
            $e = [System.IO.Path]::GetExtension($f).ToLowerInvariant()
            if ($e) { $extCount[$e] = 1 + [int]$extCount[$e] }
        }
    }
}

function Get-LangCount($tool) {
    $n = 0
    foreach ($e in $tool.Ext) { $n += [int]$extCount[$e] }
    $n
}

Write-Host ''
if ($inRepo) { Write-Host "Languages found in $(Get-Location):" -ForegroundColor Cyan }
else { Write-Host 'Not inside a git repository: language counts unavailable, decide from what you code in.' -ForegroundColor Yellow }

$missing = @()
$lastGroup = ''
foreach ($t in $tools) {
    $have = Test-Program $t.Exe
    $ver = if ($have) { Test-ToolRuns $t.Name } else { $null }
    if ($t.Group -ne $lastGroup) { Write-Host "`n$($t.Group)" -ForegroundColor Cyan; $lastGroup = $t.Group }
    $used = ''
    if ($t.Ext.Count -gt 0 -and $inRepo) {
        $c = Get-LangCount $t
        $used = if ($c -gt 0) { "  [$c file(s) in this repo]" } else { '  [none in this repo]' }
    }
    if ($have) { $mark = ' - ' }
    else { $missing += $t; $mark = "{0,2}." -f $missing.Count }
    $state = if ($ver) { "ok: $ver" } elseif ($have) { 'FOUND BUT FAILS TO RUN' } else { 'missing' }
    $color = if ($ver) { 'Green' } elseif ($have) { 'Red' } else { 'Gray' }
    Write-Host ("  {0} {1,-9} {2,-34} " -f $mark, $t.Name, $t.Does) -NoNewline
    Write-Host $state -ForegroundColor $color -NoNewline
    Write-Host $used
}
Write-Host ''

function Show-VerifyNote {
    Write-Host ''
    Write-Host 'To check later, in a NEW terminal (green "ok: <version>" means it runs):' -ForegroundColor Cyan
    Write-Host '  .\Install-Scanners.ps1                  re-run this menu; each tool shows its version or why not'
    Write-Host '  ruff --version ; mypy --version ; eslint --version ; tsc --version'
    Write-Host '  gitleaks version ; semgrep --version ; jscpd --version ; trivy --version'
    Write-Host 'A tool that prints a version is ready. "not recognized" means PATH has not picked it up: open a new'
    Write-Host 'terminal (and restart Claude Code from it). In /code-audit, a tool that still cannot run shows as "skipped".'
}

if ($missing.Count -eq 0) { Write-Host 'Everything is installed.'; Show-VerifyNote; return }

$ans = (Read-Host 'Install which? Numbers like 1,3  |  all  |  Enter for none').Trim().ToLowerInvariant()
if (-not $ans) { Write-Host 'Nothing installed.'; Show-VerifyNote; return }
$picked = if ($ans -eq 'all') { $missing }
          else {
              $nums = $ans -split '[,\s]+' | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ }
              @($nums | Where-Object { $_ -ge 1 -and $_ -le $missing.Count } | Sort-Object -Unique | ForEach-Object { $missing[$_ - 1] })
          }
if (-not $picked) { Write-Host 'No valid choice; nothing installed.'; Show-VerifyNote; return }

foreach ($t in $picked) {
    $cmd = $t.Cmd | Where-Object { Test-Program $_.Prog } | Select-Object -First 1
    if (-not $cmd) {
        Write-Host "$($t.Name): no installer found ($(($t.Cmd | ForEach-Object { $_.Prog }) -join ' / ')). Run by hand: $($t.Cmd[0].Line)" -ForegroundColor Yellow
        continue
    }
    Write-Host "  > $($cmd.Line)" -ForegroundColor DarkGray
    try {
        & ([scriptblock]::Create($cmd.Line))
        if ($LASTEXITCODE -ne 0) { Write-Host "  $($t.Name): installer exited with code $LASTEXITCODE" -ForegroundColor Red }
        else { Write-Host "  $($t.Name) installed (open a new terminal if it is not found yet)" -ForegroundColor Green }
    }
    catch { Write-Host "  $($t.Name) failed: $($_.Exception.Message)" -ForegroundColor Red }
}

Write-Host "`nChecking what you just installed:" -ForegroundColor Cyan
foreach ($t in $picked) {
    $v = Test-ToolRuns $t.Name
    if ($v) { Write-Host ("  {0,-9} ok: {1}" -f $t.Name, $v) -ForegroundColor Green }
    else { Write-Host ("  {0,-9} not runnable in this terminal yet - open a new terminal and re-run this script" -f $t.Name) -ForegroundColor Yellow }
}
Show-VerifyNote
