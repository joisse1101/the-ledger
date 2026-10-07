## Why

`Install-Skills.ps1` copies the toolkit into `~/.claude` or `<project>/.claude`, but it cannot tell you
where things are installed or whether the install works. `-List` answers for one scope per run, so a
project copy shadowing a drifted global copy goes unseen; a partial install leaves `/code-audit` broken
with no warning; and nothing checks that git, Python and a shell (needed by the agent hooks) exist or that
the installed engine launches. The global path is also untestable because it hard-codes `$HOME`. Without
a trustworthy install-and-verify step, the end-to-end code audit cannot be called complete.

## What Changes

- `-List` and the wizard's "Check" show a **matrix**: one row per toolkit item, a global column and a
  project column, with `missing` / `up to date` / `differs`, plus a note when both scopes hold the item
  (`both (same)` or `project shadows global (differs)`).
- A per-scope **completeness verdict** for `/code-audit` (skill + `sec-checker` + `arch-checker` +
  command): `complete`, `incomplete (missing: ...)` or `absent`. The wizard warns when a partial pick
  would leave it incomplete.
- A **preflight** that warns (never blocks) when git, a Python that actually runs (not just a WindowsApps
  stub on PATH) or a POSIX `sh` is missing.
- A **verify step** after install: the completeness check, then a smoke test that runs the installed
  `audit.py --init` in a throwaway temp git repo and checks it exits 0 with JSON, then deletes the repo.
- A closing **summary** naming the scope, counts (installed / updated / skipped / unchanged), the verify
  result and "restart Claude Code"; project installs also say `.claude/` was written into the repo.
- Flag-mode `-Uninstall` asks for confirmation unless `-Force` is given.
- A `-ClaudeHome <dir>` parameter replacing `~` for global destinations, so dry runs and tests never touch
  the real `~/.claude`.
- A plain-PowerShell **test script** (exits non-zero on failure, no Pester dependency) under
  `toolkit/install/tests/`, run against `-ClaudeHome` and temp project folders.
- `toolkit/README.md` and `wiki/Repository-Layout.md` updated to match.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-skills`: the status-listing requirement now covers both scopes at once with shadow and
  completeness reporting; new requirements for post-install verification, preflight warnings, a global
  destination override, and confirmed uninstall.

## Impact

- `toolkit/install/Install-Skills.ps1` (main work), new `toolkit/install/tests/`, `toolkit/README.md`,
  `wiki/Repository-Layout.md`.
- `Install-Scanners.ps1` and `targets.json` are untouched. No change to `audit.py`, the agents, the
  command, or Claude Code settings.
- No new runtime dependencies. Existing flags keep working; `-List` output format changes (it gains a
  column), so anything parsing it breaks (nothing in the repo does).

## Assumptions

- Preflight warns rather than blocks, since Python can be fixed after installing.
- The test script is plain PowerShell rather than Pester, to avoid depending on Pester 5 (Windows
  PowerShell 5.1 ships Pester 3).
- With no `-Path`, the project column uses the current git repo's root, or `n/a` outside one.
