<#
Claude Code PreToolUse hook that relays a tool-permission decision to the Ledger dashboard. Reads
the hook's JSON payload from stdin and POSTs the session's tool call to the local Ledger API
(http://127.0.0.1:<port>, where port is -Port, else $env:LEDGER_PORT, else 8501; the installer bakes
-Port in from the repo's .env). If that session's control view is open in a
browser, the API holds the request until someone approves/denies there, and this script turns the
answer into hookSpecificOutput.permissionDecision ("allow" or "deny" plus a reason).

Any other outcome - nobody watching, no answer in time, backend not running, a malformed payload -
prints NOTHING and exits 0, so Claude Code decides exactly as it would without this hook. That
includes never printing "ask": that is itself a decision, and would turn a silently pre-allowed
tool call into a prompt.

Optional and dashboard-coupled, unlike the standalone toast scripts in hooks/scripts/; installed
separately (see hooks/README.md). Register it with a hook timeout comfortably above
-TimeoutSeconds, or Claude Code kills it mid-wait.
#>
param(
    # A few seconds above the API's own wait (pending_decisions.DECISION_WAIT_SECONDS = 120), so the
    # API's "no opinion" reply normally arrives first instead of this client giving up on it.
    [int]$TimeoutSeconds = 125,
    # The API's port. 0 = not given: fall back to $env:LEDGER_PORT, then 8501.
    [int]$Port = 0
)

$ErrorActionPreference = 'Stop'

try {
    # Read stdin as UTF-8 explicitly: [Console]::In uses the OEM code page on Windows PowerShell 5.1
    # and would mangle non-ASCII tool input.
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
    $payload = $reader.ReadToEnd() | ConvertFrom-Json

    $sessionId = [string]$payload.session_id
    $toolName = [string]$payload.tool_name
    # The API's route only accepts [A-Za-z0-9-]{1,64}; anything else can't be answered from the app.
    if ($sessionId -notmatch '^[A-Za-z0-9-]{1,64}$' -or -not $toolName) { exit 0 }

    $toolInput = $payload.tool_input
    if ($null -eq $toolInput) { $toolInput = [ordered]@{} }

    $port = if ($Port -gt 0) { $Port } elseif ($env:LEDGER_PORT -match '^\d+$') { [int]$env:LEDGER_PORT } else { 8501 }
    $uri = "http://127.0.0.1:$port/api/sessions/$([System.Uri]::EscapeDataString($sessionId))/decisions"

    # Fail fast when the backend isn't running: on Windows a refused loopback connect is retried
    # for ~2s before HttpWebRequest reports it, and this runs before every matched tool call. A
    # listening backend accepts at the kernel level immediately, so 250ms is generous.
    $probe = New-Object System.Net.Sockets.TcpClient
    try {
        if (-not ($probe.ConnectAsync('127.0.0.1', $port).Wait(250) -and $probe.Connected)) { exit 0 }
    } catch {
        exit 0
    } finally {
        $probe.Dispose()
    }

    $json = [ordered]@{ tool_name = $toolName; tool_input = $toolInput } | ConvertTo-Json -Depth 32 -Compress
    $body = [System.Text.Encoding]::UTF8.GetBytes($json)

    # A raw HttpWebRequest rather than Invoke-RestMethod: on Windows PowerShell 5.1 the cmdlet adds
    # ~2s (proxy detection, cmdlet setup) to every call - and this runs before every matched tool
    # call. Proxy = $null skips proxy lookup for a loopback address.
    $request = [System.Net.HttpWebRequest]::Create($uri)
    $request.Method = 'POST'
    $request.Proxy = $null
    $request.Timeout = $TimeoutSeconds * 1000
    $request.ContentType = 'application/json; charset=utf-8'
    # X-Requested-With is required on every non-GET request, local or not (api/security.py).
    $request.Headers.Add('X-Requested-With', 'ledger')
    $request.ContentLength = $body.Length
    $requestStream = $request.GetRequestStream()
    try { $requestStream.Write($body, 0, $body.Length) } finally { $requestStream.Dispose() }

    $webResponse = $request.GetResponse()
    try {
        $responseReader = New-Object System.IO.StreamReader($webResponse.GetResponseStream(), [System.Text.Encoding]::UTF8)
        $response = $responseReader.ReadToEnd() | ConvertFrom-Json
    } finally {
        $webResponse.Dispose()
    }

    $decision = [string]$response.decision
    if ($decision -ne 'allow' -and $decision -ne 'deny') { exit 0 }

    $output = [ordered]@{
        hookEventName      = 'PreToolUse'
        permissionDecision = $decision
    }
    if ($decision -eq 'deny' -and $response.reason) {
        $output.permissionDecisionReason = [string]$response.reason
    } elseif ($decision -eq 'allow') {
        $output.permissionDecisionReason = 'Approved from the Ledger dashboard'
    }

    $result = [ordered]@{ hookSpecificOutput = $output } | ConvertTo-Json -Depth 5 -Compress
    # Escape non-ASCII so the output survives whatever code page stdout uses.
    $result = [regex]::Replace($result, '[^\x00-\x7F]', { param($m) '\u{0:x4}' -f [int][char]$m.Value })
    [Console]::Out.Write($result)
} catch {
    # Backend down, timeout, bad payload...: silent pass-through, no retry.
}
exit 0
