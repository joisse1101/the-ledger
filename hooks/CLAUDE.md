# hooks/ — Claude Code hooks and scripts

| Working on | Read |
|---|---|
| Toast hooks, chime script, relay hook, backup-task scripts | [Hooks](../wiki/Services/Hooks.md) |
| Install, uninstall, test steps | `README.md` in this folder |
| Prompts answered from the dashboard | [Backend: live sessions and prompts](../wiki/Backend/Live-Sessions-And-Prompts.md) |

## Local rules

- `hooks/ledgerScripts/Relay-PermissionRequest.ps1` must print nothing and exit 0 whenever it has no
  answer (backend down, timeout, any error). Any output is treated as a decision.
- `scripts/` is standalone and unrelated to the dashboard, except that `api/` runs
  `hooks/scripts/Open-ClaudeRepoWindow.ps1`. Don't move or change it without checking `api/app/routers/sessions.py`.
- `ledgerScripts/` is dashboard-coupled. Keep it apart from `scripts/`.
- `hooks/chimeScripts/Play-ClaudeChime.ps1` must print nothing and exit 0 on every path. Its
  `-DryRun`, `-IdleSeconds`, `-StateDir` and `-PlayerPath` parameters are test-only; tests never play a sound. Its sound child must open no window (`CreateNoWindow`) and announces itself as `Ledger: Playing chimes...`.
- `chimeScripts/` is standalone like `scripts/`, not dashboard-coupled. Keep it apart from `ledgerScripts/`.
- Every process the Ledger starts carries a no-window marker on the same call: `creationflags=NO_WINDOW`
  in Python, `-NoNewWindow` on `Start-Process` or `CreateNoWindow = $true` on a `ProcessStartInfo`, and
  window style `0` on a `.vbs` `Run`. `-WindowStyle Hidden` does not count; Windows Terminal ignores it.
  `api/tests/test_no_window_guard.py` enforces this over `hooks/`, `widget/`, `api/app` and the root
  scripts. Its `ALLOWED` list names the deliberate windows (the `Start-Ledger.ps1` backend and frontend
  windows, the widget's Electron window); add a line there with a reason only for a window the user asked to see.
- Relay hook behavior was verified against a specific Claude Code version; re-check after upgrades.
