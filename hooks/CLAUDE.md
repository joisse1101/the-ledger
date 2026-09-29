# hooks/ — Claude Code hooks and scripts

| Working on | Read |
|---|---|
| Toast hooks, relay hook, backup-task scripts | [Hooks](../wiki/Hooks.md) |
| Install, uninstall, test steps | `README.md` in this folder |
| Prompts answered from the dashboard | [Backend-Live-Sessions-And-Prompts](../wiki/Backend-Live-Sessions-And-Prompts.md) |

## Local rules

- `hooks/ledgerScripts/Relay-PermissionRequest.ps1` must print nothing and exit 0 whenever it has no
  answer (backend down, timeout, any error). Any output is treated as a decision.
- `scripts/` is standalone and unrelated to the dashboard, except that `api/` runs
  `hooks/scripts/Open-ClaudeRepoWindow.ps1`. Don't move or change it without checking `api/server.py`.
- `ledgerScripts/` is dashboard-coupled. Keep it apart from `scripts/`.
- Relay hook behavior was verified against a specific Claude Code version; re-check after upgrades.
