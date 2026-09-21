## Why

The `Notification` and `Stop` toasts say that Claude needs you or has finished, but nothing about how much it is sending. Context size is the number that tells you when a session is getting heavy and worth compacting, and a toast is where you already look at a glance, including when the dashboard isn't open. The `live-context-gauge` change covers the dashboard; this covers the toast.

## What Changes

- Both toasts gain a third text line: `Context 394k`, the size of everything sent on the session's latest request (fresh input + cache read + cache written), read from the session's transcript when the hook fires.
- If the transcript can't be found or read, or it has no usable turn yet, the line is omitted and the toast is otherwise unchanged. The token lookup must never delay or break the notification.
- `hooks/README.md` is updated: the script's description, and a test that shows the new line.

The toast title, body template, click-to-focus behavior, `settings.json` hook entries, and the installer are unchanged.

### Out of scope

- Growth since the last prompt, and session cumulative totals. Cumulative totals are dominated by repeated cache reads and don't describe what's being sent.
- Cost, percentages, context-window sizes, or threshold-based alerts.
- Any change to the Streamlit app.

## Capabilities

### New Capabilities
- `toast-context-line`: the hook toasts show the session's current context size as an extra line, and degrade to the existing toast when it can't be determined.

### Modified Capabilities

None. There are no existing specs under `openspec/specs/`.

## Impact

- `hooks/scripts/Send-ClaudeToast.ps1`: reads `transcript_path` from the hook's stdin JSON, tail-reads the transcript, and adds the third text line.
- `hooks/README.md`: description and a new test; the existing Test 2 only pipes `cwd`, so it still exercises the no-token path.
- Existing installs need one re-run of `hooks/Install-ClaudeHooks.ps1` to refresh the copy in `~/.claude/hooks/` (the repo copy and installed copy are currently identical).
- Shares its definition of "context" with `live-context-gauge` (`claude_context.py`). The hook can't import it, so the rule is restated in PowerShell.
- No new dependencies. BurntToast is already required.
