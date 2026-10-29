## Context

See proposal.md for the motivation. Today `Start-Ledger.ps1`, `widget\Start-Widget.ps1` and
`hooks\Install-ClaudeHooks.ps1` each carry their own copy of the `.env` parser and `Resolve-Port`.
`Start-Widget.ps1` only tests that `widget\node_modules` exists, and it runs hidden from the
shortcut, so a failed install is invisible. The widget adopts a backend that is already answering
and never stops one it did not start. `Stop-Ledger.ps1` stops only the PIDs in `.ledger-run.json`,
which is deleted on stop. The relay hook's backend port is baked into its `settings.json` command at
install time. PowerShell scripts are tested either as subprocesses from pytest
(`api\tests\test_hook_install.py`) or with a standalone script (`widget\tests\Test-StartWidget.ps1`).

## Goals / Non-Goals

**Goals:**
- One shared helper so port, `.env` and dependency logic exists once.
- Start and the shortcut path both repair dependencies, so no entry point can fail silently on a
  half-installed machine.
- Every start verifies its result and reports it, with a failure exit code.

**Non-Goals:**
- Installing Python, Node or Docker for the user.
- Changing how the relay hook finds its port (see Decisions).
- Making the widget shortcut start the frontend; it stays widget plus backend.
- Replacing the helper scripts; they stay, non-interactive.

## Decisions

**Shared helper in a new top-level `scripts/` folder.** A single file dot-sourced by the root scripts
and by the widget and hooks scripts. Chosen by the user over keeping it at the root (beside
`Start-Ledger.ps1`) because it keeps root tooling to the entry points. It costs the "exactly five
top-level folders" rule, so `CLAUDE.md`, `wiki\Repository-Layout.md` and any `check_docs.py` check
that lists folders change in the same commit. Alternative of copying the logic into each script was
rejected as the current duplication.

**Sticky ports in a separate gitignored file at the repo root.** `.ledger-run.json` holds PIDs and is
deleted on stop, so it cannot carry a choice across runs, and `.env` is the user's own config, so the
tool does not write into it. Precedence is parameter, `.env`, saved file, scan of 8501-8599. The scan
tests a port by trying to bind it; the small gap between "free" and "bound by the backend" is accepted
and a bind failure surfaces through the backend's own error. A saved port that is busy is probed at
`/api/meta` to tell this app's backend (reuse) from anything else (re-pick). Alternative of picking
new ports every run was rejected: the widget shortcut, the relay hook and bookmarks would go stale.

**Dependency check compares artifacts to a stamp.** For the venv, check the interpreter exists and a
stamp recording the hash of `requirements*.txt` matches. For `web\` and `widget\`, check
`node_modules` is non-empty and a stamp of `package-lock.json` matches, then `widget\` also checks
`electron.exe`. A missing or mismatched stamp triggers `pip install -r` or `npm ci`. Alternative of
always reinstalling was rejected as slow; alternative of checking folder existence is the bug being
fixed. The stamps live inside the folders they describe so deleting a folder resets its stamp.

**Start-Ledger launches the widget last and records its PID only if it launched one.** The widget
starts after the backend answers, reusing the wait loop `-Remote` already has, otherwise it would
start its own hidden backend and collide with the window one. The widget is single-instance: when one
is already running the launch only brings it forward, so no PID is recorded and Stop leaves it alone.
`Start-Widget.ps1 -PassThru` already returns the process for this. The widget PID is added to
`.ledger-run.json`.

**Interactive offers check for a console.** The stale relay-hook offer asks only when a console is
attached and input is not redirected, and reinstalls with a printed notice when not or when `-Yes` is
passed. A prompt that hangs a hidden or scheduled start is worse than the staleness it fixes, and
reinstalling only restores a choice the user already made. Stale is detected by reading the `-Port`
baked into the installed relay hook's command in `settings.json` and comparing it to the chosen
backend port.

**Installer owns all prompts; helpers take switches.** `Install-Ledger.ps1` asks and calls the
existing install scripts with their non-interactive switches. Where a helper has no such switch it
gets one (for example a quiet or force switch) rather than a prompt of its own. The installer does the
prerequisite and dependency steps by calling the shared helper, and for the shortcut also pre-warms
the widget's packages so the first hidden launch is not a long silent `npm ci`.

**Prerequisite check reads minimums from the repo.** Python and Node are checked for presence and
for the versions the repo declares, not hardcoded numbers; Docker is checked only for `-Remote`. On
failure the script prints the vendor's download page and exits non-zero before touching anything.

**Relay hook keeps its baked port.** Reading the saved ports file at fire time would remove the stale
case entirely, but changes `Relay-PermissionRequest.ps1`, which must print nothing and exit 0 on any
failure. Left as a possible follow-up; the reinstall offer covers the gap for now.

## Risks / Trade-offs

- [Moving default ports breaks old bookmarks and any docs or scripts naming 4173 or 8080] → update
  the ten real default sites and the docs in the same change; test fixtures using those numbers as
  sample data are left alone.
- [`scripts/` breaks the five-folder rule] → documented update to the layout docs; the helper has one
  stable path and a small contract.
- [The relay hook goes stale after a conflict-driven re-pick] → Start offers or performs a reinstall;
  the installer repeats the offer on re-run.
- [Start-Ledger now does more before launching, so a start is slower when repairs run] → repairs run
  only when a stamp or artifact is wrong; a current setup costs only the checks.
- [Removing `-InstallBackupTask` breaks scripts that pass it] → called out as breaking in the
  proposal; the installer is the single route and `Stop-Ledger.ps1 -UninstallBackupTask` is untouched.
- [Bind-then-use race on a scanned port] → accepted; a collision shows as the backend's bind error
  and the next start re-picks.

## Migration Plan

Existing installs keep working: with no saved ports file, the first start scans and saves. An
existing `.env` pin still wins. Users with a relay hook installed get the reinstall offer on the first
start after the port changes. Rollback is reverting the change; the saved ports file and stamps are
gitignored and harmless.
