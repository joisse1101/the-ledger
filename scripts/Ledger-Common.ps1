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

function Test-Prerequisites {
    # Prints each missing prerequisite with where to install it and returns $false if any is missing,
    # so the caller can stop before touching anything. See Get-MissingPrerequisites for the switches.
    param(
        [switch]$Remote,
        [scriptblock]$Resolver = { param($command) [bool](Get-Command $command -ErrorAction SilentlyContinue) }
    )
    $missing = @(Get-MissingPrerequisites -Remote:$Remote -Resolver $Resolver)
    foreach ($tool in $missing) {
        Write-Host "$($tool.Name) is not installed. Download it from $($tool.Url)"
    }
    return ($missing.Count -eq 0)
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

# Ports the app picks from when nothing is configured or saved.
$script:LedgerPortRange = 8501..8599
# Chosen ports survive between runs here (gitignored); .ledger-run.json is deleted on stop.
$script:LedgerPortsFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.ledger-ports.json'

function Get-SavedPorts {
    # The saved choice as a hashtable of name -> port; a missing file is no choice yet, an
    # unreadable one is an error for the caller to see.
    param([string]$Path = $script:LedgerPortsFile)
    $saved = @{}
    if (-not (Test-Path $Path)) { return $saved }
    $parsed = Get-Content $Path -Raw | ConvertFrom-Json
    foreach ($property in $parsed.PSObject.Properties) { $saved[$property.Name] = [int]$property.Value }
    return $saved
}

function Save-Port {
    param([string]$Name, [int]$Port, [string]$Path = $script:LedgerPortsFile)
    $saved = Get-SavedPorts -Path $Path
    $saved[$Name] = $Port
    $saved | ConvertTo-Json | Set-Content -Path $Path -Encoding utf8
}

function Test-PortFree {
    # Free means bindable on loopback (where the backend listens) and on every interface (where the
    # gateway publishes); Windows lets the second succeed while another process holds the first.
    param([int]$Port)
    foreach ($address in @([Net.IPAddress]::Loopback, [Net.IPAddress]::Any)) {
        $listener = New-Object Net.Sockets.TcpListener($address, $Port)
        try {
            $listener.Start()
        } catch [Net.Sockets.SocketException] {
            return $false
        } finally {
            $listener.Stop()
        }
    }
    return $true
}

function Test-LedgerBackend {
    # True when something on the port answers /api/meta the way this app's backend does.
    param([int]$Port)
    try {
        $meta = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/meta" -TimeoutSec 3
    } catch {
        return $false
    }
    return [bool]($meta.PSObject.Properties['remote_mode'] -and $meta.PSObject.Properties['refreshed_at'])
}

function Resolve-LedgerPort {
    # Explicit parameter, then .env, then the saved port, then the first free port in the range.
    # Returns the port and where it came from; Source 'scanned' means the caller should save it.
    # A saved port that is busy stays when -ReuseWhen says what holds it is ours (the backend).
    # -Exclude keeps services of one start from being handed the same scanned port.
    param(
        [int]$Explicit,
        [string]$Name,
        [hashtable]$EnvFileValues = @{},
        [hashtable]$SavedPorts = @{},
        [int[]]$Exclude = @(),
        [scriptblock]$IsFree = { param($port) Test-PortFree -Port $port },
        [scriptblock]$ReuseWhen = { param($port) $false }
    )
    if ($Explicit) { return [PSCustomObject]@{ Port = $Explicit; Source = 'parameter' } }
    if ($EnvFileValues.ContainsKey($Name)) { return [PSCustomObject]@{ Port = [int]$EnvFileValues[$Name]; Source = 'env' } }

    if ($SavedPorts.ContainsKey($Name)) {
        $saved = [int]$SavedPorts[$Name]
        if (($saved -notin $Exclude) -and ((& $IsFree $saved) -or (& $ReuseWhen $saved))) {
            return [PSCustomObject]@{ Port = $saved; Source = 'saved' }
        }
    }

    foreach ($candidate in $script:LedgerPortRange) {
        if (($candidate -notin $Exclude) -and (& $IsFree $candidate)) {
            return [PSCustomObject]@{ Port = $candidate; Source = 'scanned' }
        }
    }
    throw "No free port left in $($script:LedgerPortRange[0])-$($script:LedgerPortRange[-1]) for $Name."
}

# Stamps live inside the folder they describe, so deleting the folder resets the stamp.
$script:VenvStampName = '.requirements-stamp'
$script:NpmStampName = '.lock-stamp'

function Get-ElectronPath {
    param([string]$RepoRoot)
    Join-Path $RepoRoot 'widget\node_modules\electron\dist\electron.exe'
}

function Test-VenvCurrent {
    # The interpreter exists and the requirements are the ones last installed.
    param([string]$RepoRoot)
    $apiDir = Join-Path $RepoRoot 'api'
    $venvDir = Join-Path $apiDir '.venv'
    if (-not (Test-Path (Join-Path $venvDir 'Scripts\python.exe'))) { return $false }
    $requirements = Get-ChildItem -Path $apiDir -Filter 'requirements*.txt' | Sort-Object Name | ForEach-Object FullName
    return (Test-Stamp -StampPath (Join-Path $venvDir $script:VenvStampName) -Value (Get-FilesStamp -Path $requirements))
}

function Test-NpmCurrent {
    # node_modules holds packages (not just the stamp) and they are the lockfile's.
    param([string]$ProjectDir)
    $modulesDir = Join-Path $ProjectDir 'node_modules'
    if (-not (Test-Path $modulesDir)) { return $false }
    $packages = @(Get-ChildItem -LiteralPath $modulesDir -Force | Where-Object Name -ne $script:NpmStampName)
    if ($packages.Count -eq 0) { return $false }
    $lockStamp = Get-FilesStamp -Path (Join-Path $ProjectDir 'package-lock.json')
    return (Test-Stamp -StampPath (Join-Path $modulesDir $script:NpmStampName) -Value $lockStamp)
}

function Get-DependencyRepairs {
    # The ordered steps needed to bring the chosen components ('api', 'web', 'widget') up to date;
    # nothing when everything is current. Electron is planned whenever its binary is missing and is
    # skipped at run time if the npm step already fetched it.
    param([string]$RepoRoot, [string[]]$Component = @('api', 'web', 'widget'))
    $steps = New-Object System.Collections.Generic.List[object]
    function Add-Step([string]$Name, [string]$Action, [string]$Directory) {
        $steps.Add([PSCustomObject]@{ Component = $Name; Action = $Action; Directory = $Directory })
    }
    $apiDir = Join-Path $RepoRoot 'api'
    if (('api' -in $Component) -and -not (Test-VenvCurrent -RepoRoot $RepoRoot)) {
        if (-not (Test-Path (Join-Path $apiDir '.venv\Scripts\python.exe'))) { Add-Step 'api' 'venv' $apiDir }
        Add-Step 'api' 'pip' $apiDir
    }
    foreach ($name in @('web', 'widget')) {
        $projectDir = Join-Path $RepoRoot $name
        if (($name -in $Component) -and -not (Test-NpmCurrent -ProjectDir $projectDir)) { Add-Step $name 'npm' $projectDir }
    }
    if (('widget' -in $Component) -and -not (Test-Path (Get-ElectronPath -RepoRoot $RepoRoot))) {
        Add-Step 'widget' 'electron' (Join-Path $RepoRoot 'widget')
    }
    return $steps.ToArray()
}

function Get-DependencyStepText {
    param($Step)
    switch ($Step.Action) {
        'venv'     { return "Creating the backend's Python environment" }
        'pip'      { return "Installing the backend requirements" }
        'npm'      { return "Installing the $($Step.Component) packages (npm ci)" }
        'electron' { return "Fetching the Electron binary" }
    }
}

function Invoke-DependencyStep {
    # Runs one repair step for real; $true when its command succeeded.
    param($Step)
    Push-Location $Step.Directory
    try {
        switch ($Step.Action) {
            'venv'     { & python -m venv .venv }
            'pip'      { & (Join-Path $Step.Directory '.venv\Scripts\python.exe') -m pip install -r requirements-dev.txt }
            'npm'      { & npm ci }
            'electron' { & node (Join-Path $Step.Directory 'node_modules\electron\install.js') }
        }
        return ($LASTEXITCODE -eq 0)
    } finally {
        Pop-Location
    }
}

function Invoke-DependencyRepair {
    # Applies Get-DependencyRepairs, saying what it does, recording a stamp after each successful
    # install, and throwing when a step fails so the caller starts nothing. -Installer takes a step
    # and returns success; tests pass a fake so no network or real install is involved.
    param(
        [string]$RepoRoot,
        [string[]]$Component = @('api', 'web', 'widget'),
        [scriptblock]$Installer = { param($step) Invoke-DependencyStep -Step $step }
    )
    foreach ($step in (Get-DependencyRepairs -RepoRoot $RepoRoot -Component $Component)) {
        if ($step.Action -eq 'electron' -and (Test-Path (Get-ElectronPath -RepoRoot $RepoRoot))) { continue }
        $text = Get-DependencyStepText -Step $step
        Write-Host "$text..."
        if (-not (& $Installer $step)) {
            throw "$text failed. Check your network connection and try again; nothing was started."
        }
        if ($step.Action -eq 'electron' -and -not (Test-Path (Get-ElectronPath -RepoRoot $RepoRoot))) {
            throw "The Electron binary is missing and could not be downloaded; nothing was started."
        }
        Save-DependencyStamp -Step $step
    }
}

function Save-DependencyStamp {
    param($Step)
    if ($Step.Action -eq 'pip') {
        $requirements = Get-ChildItem -Path $Step.Directory -Filter 'requirements*.txt' | Sort-Object Name | ForEach-Object FullName
        Write-Stamp -StampPath (Join-Path $Step.Directory ".venv\$script:VenvStampName") -Value (Get-FilesStamp -Path $requirements)
    } elseif ($Step.Action -eq 'npm') {
        $lockStamp = Get-FilesStamp -Path (Join-Path $Step.Directory 'package-lock.json')
        Write-Stamp -StampPath (Join-Path $Step.Directory "node_modules\$script:NpmStampName") -Value $lockStamp
    }
}
