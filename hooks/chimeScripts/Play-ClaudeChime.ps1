<#
.SYNOPSIS
Plays a short Windows sound when a Claude Code session finishes or needs input, but only when the
user is away from the PC.

.DESCRIPTION
Run by Claude Code's Stop hook (-Kind done) and Notification hook (-Kind needs-input), see
hooks\Install-ClaudeHooks.ps1 -IncludeChimes. Prints nothing and exits 0 on every path: anything on
stdout or a failure could disturb Claude Code, so a top-level try/catch swallows everything.

Order of decisions:
1. Away check. Away = no keyboard/mouse input for 300 seconds or more (GetLastInputInfo), or a valid
   AFK flag (afk.flag in the state folder, holding a UTC expiry time). Unreadable idle time counts as
   away. A present user stops here and leaves no state behind.
2. Merge. Under a named mutex, one timestamp file per kind in the state folder: 'done' is skipped if
   any sound played in the last 5 seconds, 'needs-input' only if a needs-input sound did. If the mutex
   cannot be taken quickly, or the state folder is unusable, the sound plays.
3. Play. A hidden child PowerShell plays System.Media.SystemSounds (Asterisk for done, Hand for
   needs-input), so the hook returns at once.

.PARAMETER Kind
'done' or 'needs-input'. Anything else does nothing.

.PARAMETER DryRun
Test only. Prints 'play', 'skip-present' or 'skip-merged' instead of playing.

.PARAMETER IdleSeconds
Test only. Replaces the real idle clock. A negative value means "idle time cannot be read".

.PARAMETER StateDir
Test only. Replaces the state folder (default: %USERPROFILE%\.claude\hooks\chimeScripts\state).

.PARAMETER PlayerPath
Test only. Replaces the program that plays the sound, so tests can break or fake the sound call.

.EXAMPLE
'{"cwd":"C:\\repo"}' | .\Play-ClaudeChime.ps1 -Kind done -DryRun -IdleSeconds 400
#>
[CmdletBinding()]
param(
    [string]$Kind,
    [switch]$DryRun,
    [int]$IdleSeconds,
    [string]$StateDir,
    [string]$PlayerPath = 'powershell.exe'
)

$AwayAfterSeconds = 300
$MergeWindowSeconds = 5
$MutexName = 'Local\ClaudeChimeMerge'
$MutexWaitMilliseconds = 500
$SoundByKind = @{ 'done' = 'Asterisk'; 'needs-input' = 'Hand' }

# Whole seconds since the last keyboard/mouse input, or $null when Windows won't say.
function Get-IdleSeconds {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ChimeIdle {
    [StructLayout(LayoutKind.Sequential)]
    struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
    [DllImport("user32.dll")] static extern bool GetLastInputInfo(ref LASTINPUTINFO info);
    [DllImport("kernel32.dll")] static extern uint GetTickCount();
    // Unsigned subtraction, so the 49-day tick counter wrap is harmless. -1 = unreadable.
    public static long IdleMilliseconds() {
        LASTINPUTINFO info = new LASTINPUTINFO();
        info.cbSize = (uint)Marshal.SizeOf(typeof(LASTINPUTINFO));
        if (!GetLastInputInfo(ref info)) return -1;
        return unchecked(GetTickCount() - info.dwTime);
    }
}
'@
    $milliseconds = [ChimeIdle]::IdleMilliseconds()
    if ($milliseconds -lt 0) { return $null }
    return [long][Math]::Floor($milliseconds / 1000)
}

# True only for a readable afk.flag whose UTC expiry is still in the future.
function Test-AfkFlag {
    param([string]$Folder)
    try {
        $path = Join-Path $Folder 'afk.flag'
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
        $text = (Get-Content -LiteralPath $path -Raw -ErrorAction Stop).Trim()
        $expiry = [datetime]::Parse($text, [cultureinfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
        return $expiry -gt [datetime]::UtcNow
    } catch {
        return $false
    }
}

function Test-IsAway {
    param([string]$Folder)
    if ($script:IdleOverride) {
        $idle = if ($script:IdleSecondsGiven -ge 0) { $script:IdleSecondsGiven } else { $null }
    } else {
        try { $idle = Get-IdleSeconds } catch { $idle = $null }
    }
    if ($null -eq $idle) { return $true }
    if ($idle -ge $AwayAfterSeconds) { return $true }
    return (Test-AfkFlag -Folder $Folder)
}

function Test-RecentStamp {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    $stamp = [datetime]::Parse((Get-Content -LiteralPath $Path -Raw).Trim(), [cultureinfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::RoundtripKind)
    return ([datetime]::UtcNow - $stamp).TotalSeconds -lt $MergeWindowSeconds
}

# True when this alert is covered by a sound that just played; otherwise records that it will play.
# Any trouble (mutex, folder, unreadable file) means "not merged": a missed alert is worse than an extra one.
function Test-MergedAndRecord {
    param([string]$Folder, [string]$AlertKind)
    $mutex = $null
    $held = $false
    try {
        $mutex = New-Object System.Threading.Mutex($false, $MutexName)
        try { $held = $mutex.WaitOne($MutexWaitMilliseconds) } catch [System.Threading.AbandonedMutexException] { $held = $true }
        if (-not $held) { return $false }

        $ownStamp = Join-Path $Folder "$AlertKind.stamp"
        $recent = Test-RecentStamp -Path $ownStamp
        if (-not $recent -and $AlertKind -eq 'done') {
            $recent = Test-RecentStamp -Path (Join-Path $Folder 'needs-input.stamp')
        }
        if ($recent) { return $true }

        [void](New-Item -ItemType Directory -Path $Folder -Force)
        Set-Content -LiteralPath $ownStamp -Value ([datetime]::UtcNow.ToString('o')) -Encoding ASCII
        return $false
    } catch {
        return $false
    } finally {
        if ($held) { $mutex.ReleaseMutex() }
        if ($mutex) { $mutex.Dispose() }
    }
}

function Start-Sound {
    param([string]$Sound)
    # The child waits a moment because SystemSounds.Play returns before the sound ends.
    $command = "try { [System.Media.SystemSounds]::$Sound.Play(); Start-Sleep -Milliseconds 1500 } catch { }"
    Start-Process -FilePath $PlayerPath -WindowStyle Hidden `
        -ArgumentList @('-NoProfile', '-NonInteractive', '-Command', $command) | Out-Null
}

try {
    $ErrorActionPreference = 'Stop'

    # The payload is not needed, but read it so the hook runner never blocks on a full pipe.
    if ([Console]::IsInputRedirected) { [void][Console]::In.ReadToEnd() }

    if (-not $SoundByKind.ContainsKey($Kind)) { exit 0 }

    $script:IdleOverride = $PSBoundParameters.ContainsKey('IdleSeconds')
    $script:IdleSecondsGiven = $IdleSeconds
    if (-not $StateDir) {
        $StateDir = Join-Path (Join-Path $env:USERPROFILE '.claude\hooks\chimeScripts') 'state'
    }

    $decision = 'play'
    if (-not (Test-IsAway -Folder $StateDir)) {
        $decision = 'skip-present'
    } elseif (Test-MergedAndRecord -Folder $StateDir -AlertKind $Kind) {
        $decision = 'skip-merged'
    }

    if ($DryRun) {
        Write-Output $decision
    } elseif ($decision -eq 'play') {
        Start-Sound -Sound $SoundByKind[$Kind]
    }
} catch {
    # Silence is the contract: nothing may reach Claude Code.
}
exit 0
