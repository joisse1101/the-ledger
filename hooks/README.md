# Claude Code Toast Notifications

Shows a Windows toast when a Claude Code agent needs input (`Notification` hook) or finishes a task (`Stop` hook). Clicking the toast focuses the existing VS Code window for that repo, or opens a new one if it isn't already open.

The toast also shows the session's current context size as a third line (`Context 394k`): everything sent on the session's latest request (new input + cache read + cache written tokens), read from the session transcript the hook payload points to (`transcript_path`). If the transcript can't be found or read, or has no usable turn yet, the line is simply left out and the toast is otherwise unchanged. It's the same number as the Context column of the app's Live sessions table.

## How it works

`New-BurntToastNotification`'s click-handling (`-ActivatedAction`) only fires if the PowerShell process that created the toast is still running — but hook scripts exit right after showing the toast, so that doesn't work here. Instead, the toast is built with a **protocol-activation** click action (`claudecode://open?path=...`), which Windows resolves independently of any PowerShell process, via a custom URI protocol registered in the registry.

## 1. Scripts to share

Copy this whole `hooks\` folder to the other machine:

| File | Purpose |
|---|---|
| `scripts\Send-ClaudeToast.ps1` | Shows the toast (called by the `Notification`/`Stop` hooks), including the `Context` line when the session transcript is readable. |
| `scripts\Open-ClaudeRepoWindow.ps1` | Runs when the toast is clicked. Focuses the matching VS Code window, or opens a new one. |
| `scripts\Open-ClaudeRepoWindow.vbs` | Silent launcher — runs the above script with no console-window flash. Locates its own folder at runtime, so it works unmodified on any machine/username as long as the two `.ps1`/`.vbs` files stay together. |
| `Install-ClaudeHooks.ps1` | Copies everything in `scripts\` into `%USERPROFILE%\.claude\hooks\`, registers the protocol handler, and adds the hooks to `settings.json`. See section 3. |
| `Uninstall-ClaudeHooks.ps1` | Reverses the above. See section 5. |
| `ledgerScripts\Relay-PermissionRequest.ps1` | **Optional**, dashboard-coupled: relays a session's blocking prompts (permission dialogs, questions) to the Ledger app. Installed separately; see section 6. |


## 2. What needs to be installed

- **Claude Code** (already assumed installed)
- **VS Code**, with the `code` command available on PATH (VS Code adds this
  automatically if you check "Add to PATH" during install, or run
  `Shell Command: Install 'code' command in PATH` from the VS Code command
  palette)
- **BurntToast** PowerShell module — this is what actually renders the toast:
  ```powershell
  Install-Module -Name BurntToast -Scope CurrentUser -Force
  ```

## 3. Run the installer

```powershell
.\hooks\Install-ClaudeHooks.ps1
```

Safe to re-run — and if you installed before the `Context` line existed, re-run
it once to copy the updated `Send-ClaudeToast.ps1` over the installed one. It
does the following, all scoped to the current user (no
admin rights needed):

- **Copies the 3 scripts** into `%USERPROFILE%\.claude\hooks\` (creating the
  folder if needed).
- **Registers the `claudecode://` protocol handler.** This teaches Windows
  what to do when something launches a `claudecode://...` link — the toast's
  click action (see "How it works" above). It's the same mechanism `mailto:`
  or `slack://` links use: a registry entry (`HKCU:\Software\Classes\claudecode`)
  maps the `claudecode` scheme to a command to run, with the clicked URI
  passed in as `%1`. Here that command is the silent `.vbs` launcher, which
  in turn runs `Open-ClaudeRepoWindow.ps1` to focus/open the right VS Code
  window.
- **Merges the `Notification`/`Stop` hooks into `settings.json`** (creating
  the file if needed, without touching any hooks already there). The
  `command` written into each hook is a fully resolved, literal path to
  `Send-ClaudeToast.ps1` — the script resolves `$env:USERPROFILE` itself,
  once, while it runs in your own PowerShell session, rather than embedding
  an unresolved `$env:USERPROFILE`/`%USERPROFILE%` reference in the hook's
  `command` string. That distinction matters: Claude Code runs hook commands
  through Git Bash if it's installed, or PowerShell otherwise, and the two
  disagree on environment-variable syntax (`$USERPROFILE` vs.
  `$env:USERPROFILE` vs. `%USERPROFILE%`) — baking in the resolved path
  sidesteps that ambiguity entirely.

If you'd rather see exactly what it changes before running it, the script
is short — read `Install-ClaudeHooks.ps1` directly; it's a short run of
`New-Item`/`Set-ItemProperty`/`ConvertTo-Json` calls.

## 4. Tests

Run these on the new PC after setup, in order. Have a repo folder open in VS
Code before testing so you can check the click-to-focus behavior.

**Test 1 — BurntToast itself works:**
```powershell
New-BurntToastNotification -Text 'Test', 'BurntToast is working'
```
A toast should appear.

**Test 2 — the toast script works (without clicking):**

Run this from the repo folder you want the toast to point at (it uses
`Get-Location`, so no path to edit):
```powershell
(@{cwd = (Get-Location).Path} | ConvertTo-Json -Compress) | powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\Send-ClaudeToast.ps1" -Title "Test Alert" -BodyTemplate "Testing in {0}!"
```
A toast titled "Test Alert" mentioning the current folder name should appear.
Since this payload has no `transcript_path`, it has only those two lines, with
no `Context` line: this is also the check that the token lookup degrades
cleanly.

**Test 2b — the `Context` line:**

Same as Test 2, but the payload also names a real transcript (here, the newest
one for the current folder, so you need to have run a Claude Code session in
it):
```powershell
$transcript = Get-ChildItem "$env:USERPROFILE\.claude\projects\$((Get-Location).Path -replace '[^A-Za-z0-9]', '-')\*.jsonl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
(@{cwd = (Get-Location).Path; transcript_path = $transcript.FullName} | ConvertTo-Json -Compress) | powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\hooks\Send-ClaudeToast.ps1" -Title "Test Alert" -BodyTemplate "Testing in {0}!"
```
The toast should have a third line like `Context 394k`. Pointing
`transcript_path` at a file that doesn't exist should give the plain two-line
toast, with no error.

**Test 3 — protocol handler + click behavior (no toast needed):**

Run this from the same folder as Test 2:
```powershell
Start-Process "claudecode://open?path=$([System.Uri]::EscapeDataString((Get-Location).Path))"
```
- If that folder is already open in a VS Code window, it should be
  focused — no duplicate window, no visible console flash.
- If it isn't open, a new VS Code window should open for it — also no
  console flash.

**Test 4 — full end-to-end:**
Click the toast from Test 2. Same expected behavior as Test 3.

**Test 5 — real hook firing:**
Run a Claude Code session in that repo and let it hit a real `Notification`
(e.g. it asks a permission question) or `Stop` (it finishes a turn) event.
The toast should appear on its own, and clicking it should focus/open VS Code
for that repo.

## 5. Uninstall

```powershell
.\hooks\Uninstall-ClaudeHooks.ps1
```

Reverses section 3: removes the `Notification`/`Stop` hook entries that
reference `Send-ClaudeToast.ps1` from `settings.json` (leaving any other
hooks untouched), removes the `claudecode://` protocol handler, and deletes
just the 3 installed script files from `%USERPROFILE%\.claude\hooks\` — not
the whole folder, in case you keep other, unrelated hook scripts there too
(it removes the folder itself only if that leaves it empty).

## 6. Optional: remote prompt relay (Ledger dashboard)

Unlike everything above, this hook only does anything if the Ledger backend (`api/`) is running, and
it is **not** installed by default. It lets you answer a live session's blocking prompts - a
tool-permission dialog, or a multiple-choice question Claude asked - from the dashboard's Live list,
on this PC or (while Remote mode is on) from another device.

**What it does.** `ledgerScripts\Relay-PermissionRequest.ps1` is a `PermissionRequest` hook. Claude Code
fires that event only when a dialog is about to be shown, and runs the hook *alongside* the terminal
dialog, never in front of it, so the dialog is never hidden or delayed. The hook POSTs the prompt to the
local Ledger API (`http://127.0.0.1:<port>`, see "Port" below) and waits. If you answer in the
dashboard first, the hook hands that answer back to Claude Code: allow, allow with your chosen answers
(for a question), or deny with your reason (Claude sees it). Whichever surface answers first wins - the
terminal, the dashboard on this PC, or the dashboard on another device. In every other case - nobody
answers through the dashboard, you answer in the terminal first, the backend isn't running - the hook
prints nothing at all, so the terminal dialog is the only way to answer, exactly as without the hook.
(Any output from the hook counts as a decision; silence is what leaves the dialog alone.)

Because the hook is not stopped when a dialog is answered elsewhere, the API notices the terminal
answer from the session's transcript and releases the hook; a prompt is also dropped after 30 minutes
at most.

Both scripts print their options and examples with `-h` (or `-Help`, or `Get-Help .\hooks\Install-ClaudeHooks.ps1 -Detailed`).

**Install** (independent of the toast hooks above):

```powershell
# relay hook only
.\hooks\Install-ClaudeHooks.ps1 -IncludeSessionControl -SkipToastHooks

# toast hooks and the relay hook
.\hooks\Install-ClaudeHooks.ps1 -IncludeSessionControl
```

This copies `ledgerScripts\` to `%USERPROFILE%\.claude\hooks\ledgerScripts\` and adds a
`PermissionRequest` entry to `settings.json`. It also removes the earlier `PreToolUse`-based relay (its
`settings.json` entry and its installed script) if you had it. Safe to re-run. `-SkipToastHooks` also
skips the toast scripts and the `claudecode://` protocol handler.

**Port.** The hook has to know which port the backend is on, so the install writes it into the hook's
command as `-Port <n>`. It's resolved the way `Start-Ledger.ps1` does (highest wins): `-BackendPort`,
then `BACKEND_PORT` in the repo root's `.env`, then an already-set `BACKEND_PORT` environment
variable, then `8501`. **Re-run the install after changing `BACKEND_PORT`**, then start a new Claude
Code session: the hook reads it from `settings.json` when a session starts. If a hook is run without
`-Port` (e.g. an entry edited by hand), it falls back to the `LEDGER_PORT` environment variable, then
`8501`.

**Defaults** (edit the entry in `settings.json` afterwards to change them):

| Setting | Default | Notes |
|---|---|---|
| `matcher` | empty (every `PermissionRequest`) | The event only fires when a dialog is about to be shown, so there is nothing to narrow. |
| `timeout` | `1810` (seconds) | Must stay above the script's own wait (`-TimeoutSeconds`, default `1805`, itself just above the API's 30-minute prompt lifetime), or Claude Code kills the hook mid-wait. |
| `-Port` (in `command`) | from `.env`, else `8501` | Written by the install; see "Port" above. Without it the hook uses the `LEDGER_PORT` environment variable, then `8501`. |

The hook is machine-wide, so it fires for every session's dialogs, not only ones shown in the
dashboard. While waiting it costs one idle PowerShell process per open dialog.

**Uninstall:**

```powershell
# relay hook only (toast hooks stay)
.\hooks\Uninstall-ClaudeHooks.ps1 -IncludeSessionControl -SkipToastHooks

# toast hooks and the relay hook
.\hooks\Uninstall-ClaudeHooks.ps1 -IncludeSessionControl
```

This removes only the `PermissionRequest` entry that references `Relay-PermissionRequest.ps1` (and an
earlier `PreToolUse` relay entry, if one is still there; any other hooks stay) and deletes the
installed `ledgerScripts\` folder.

**Verified on Claude Code 2.1.281.** This relies on how that version behaves - the hook running
alongside the terminal dialog, the `updatedInput.answers` shape for a question, and a late hook result
being discarded after the dialog was already answered - established by reading its bundled schema and
by spikes, not from public documentation. **Re-check it after Claude Code upgrades** (the checks in the
`add-remote-session-control` change's task group 7 cover it). If a future version changes any of it,
the worst case is that the terminal dialog stays the only way to answer; the hook never blocks it.
