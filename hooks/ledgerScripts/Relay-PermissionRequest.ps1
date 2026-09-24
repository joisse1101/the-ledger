<#
Claude Code PermissionRequest hook that relays a blocking prompt to the Ledger dashboard. Claude Code
fires this event only when a dialog is about to be shown - a tool-permission prompt, or an
AskUserQuestion question - and runs it ALONGSIDE the terminal dialog, never in front of it. This script
reads the hook's JSON payload from stdin and POSTs {tool_name, tool_input} to the local Ledger API
(http://127.0.0.1:<port>, where port is -Port, else $env:LEDGER_PORT, else 8501; the installer bakes
-Port in from the repo's .env). The API registers the prompt and holds the request until someone
answers it in the dashboard, and this script turns that answer into
hookSpecificOutput.decision:

  allow                    -> {behavior: "allow"}
  allow, for a question    -> {behavior: "allow", updatedInput: {...tool_input, answers, annotations: {}}}
  deny (+ optional reason) -> {behavior: "deny", message: <reason>}

Whichever surface answers first wins (the terminal dialog, the dashboard on this PC, the dashboard on
another device); Claude Code discards a hook result that arrives after the dialog was already resolved.

Any other outcome - no answer, the prompt cleared because the terminal answered first, backend not
running, a malformed payload - prints NOTHING and exits 0. Output of any kind is a decision, so silence
is what leaves the terminal dialog as the only way to answer, exactly as without this hook.

TODO (tasks 7.2/7.3 of the add-remote-session-control change), not yet verified live:
  - the "terminal answered first" path: the API's transcript sweep releasing this hook with
    {decision: null}, and this script then printing nothing;
  - a multi-select answer is forwarded into updatedInput.answers as a JSON array; check what Claude
    Code's own dialog produces and, if it is a joined string, join it here rather than in the API.

Optional and dashboard-coupled, unlike the standalone toast scripts in hooks/scripts/; installed
separately (see hooks/README.md). Register it with a hook timeout comfortably above
-TimeoutSeconds, or Claude Code kills it mid-wait.
#>
param(
    # A few seconds above the API's own wait (pending_decisions.PROMPT_MAX_AGE_SECONDS = 30 minutes),
    # so the API's "no answer" reply normally arrives first instead of this client giving up on it.
    [int]$TimeoutSeconds = 1805,
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
    # for ~2s before HttpWebRequest reports it, and this runs whenever a dialog appears. A
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
    # ~2s (proxy detection, cmdlet setup) to every call. Proxy = $null skips proxy lookup for a
    # loopback address.
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

    $answer = [string]$response.decision
    if ($answer -eq 'answer') {
        if ($null -eq $response.answers) { exit 0 }
        # The question's own input, unchanged, plus the chosen answers keyed by question text - the
        # same shape the terminal dialog itself returns when a person answers.
        $updatedInput = [ordered]@{}
        foreach ($property in $toolInput.PSObject.Properties) { $updatedInput[$property.Name] = $property.Value }
        $updatedInput['answers'] = $response.answers
        $updatedInput['annotations'] = [ordered]@{}
        $decision = [ordered]@{ behavior = 'allow'; updatedInput = $updatedInput }
    } elseif ($answer -eq 'allow') {
        $decision = [ordered]@{ behavior = 'allow' }
    } elseif ($answer -eq 'deny') {
        $message = if ($response.reason) { [string]$response.reason } else { 'Denied from the Ledger dashboard' }
        $decision = [ordered]@{ behavior = 'deny'; message = $message }
    } else {
        exit 0
    }

    $result = [ordered]@{
        hookSpecificOutput = [ordered]@{ hookEventName = 'PermissionRequest'; decision = $decision }
    } | ConvertTo-Json -Depth 32 -Compress
    # Escape non-ASCII so the output survives whatever code page stdout uses.
    $result = [regex]::Replace($result, '[^\x00-\x7F]', { param($m) '\u{0:x4}' -f [int][char]$m.Value })
    [Console]::Out.Write($result)
} catch {
    # Backend down, timeout, bad payload...: silent pass-through, no retry.
}
exit 0
