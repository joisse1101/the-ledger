---
metadata:
  version: "1.0.0"
  last_updated: "2026-10-14"
paths:
  - "**/*.ps1"
  - "**/*.sh"
  - "**/*.bat"
---
# Scripts

Adds script mechanics to [core-principles](core-principles.md); it does not restate them.

- Fail fast. PowerShell: `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'`.
  Bash: `set -euo pipefail`. Batch: check `%ERRORLEVEL%` after every command that can fail.
- Make a re-run safe: check state before changing it (create if missing, skip if present) so a
  second run does nothing harmful.
- Quote every variable and path expansion (`"$path"`, `-LiteralPath`) so spaces and special
  characters do not split or expand.
- Never hardcode machine-specific paths or user names. Derive them from the script's own location
  (`$PSScriptRoot`, `"$(dirname "$0")"`) or take them as parameters.
- Never put secrets in a script or its arguments; read them from the environment.
- Validate parameters up front and print a clear error with the expected usage.
- Make destructive actions explicit: support a dry run or a confirmation, and never run a broad
  `rm -rf` or `Remove-Item -Recurse` on a variable that could be empty.
- Return a non-zero exit code on failure so callers can detect it.
- Clean up temporary files and processes on exit (`finally`, `trap`).

## Prefer

- A short usage comment or `-Help` at the top.
- Parameters over interactive prompts, so the script runs unattended.
