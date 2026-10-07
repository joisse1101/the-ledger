## Context

`Install-Skills.ps1` resolves one scope per run: `Get-DestRoot` reads `$Scope` (a script-level
variable) and `targets.json`, and `Get-ItemState` hashes a toolkit item against one destination. The
wizard only runs when no flags are passed. `/code-audit` resolves its pieces project-first, then
global, in both the command (engine lookup) and the agents' `Stop` hook (`--save-agent`), so a project
copy always wins over a global one. The global path is `~` from `targets.json` joined onto `$HOME`.
See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- One run shows where every toolkit item lives (global, project, both) and whether `/code-audit` is
  usable in each scope.
- Install ends with proof that the installed engine launches, not just that files were copied.
- The whole script, global path included, is testable without touching the real `~/.claude`.

**Non-Goals:**
- Verifying the Claude Code side (that `/code-audit` is listed, that agent hooks fire). That needs a
  live session and stays a manual step in the README.
- Running a full audit in the smoke test, installing scanners (still `Install-Scanners.ps1`), or
  supporting tools other than Claude Code beyond what `targets.json` already allows.
- Changing `audit.py`, the agents, the command or `targets.json`.

## Decisions

**Scope becomes a parameter, not ambient state.** `Get-DestRoot` takes `(kind, scope, projectRoot,
claudeHome)`; a new `Get-ScopeStates` returns, per item, the state for one scope. Status then calls it
twice (global, project) and joins on item. Alternative: keep the ambient `$Scope` and loop by
reassigning it. Rejected: the install path and the matrix would share mutable state and the tests
would have to reset it.

**`-ClaudeHome <dir>` replaces `~` for global destinations only.** Default stays `$HOME\.claude`, so
`targets.json` is unchanged: the code strips the leading `~/.claude`-style prefix from the data and
rebases it. Alternative: an env var. Rejected: invisible in `-Help` and easy to leave set. Project
scope needs no override since it already takes `-Path`.

**Project column resolves without `-Path` only for read-only views.** For `-List` and the wizard's
"Check", the project root defaults to `git rev-parse --show-toplevel`, else the column is `n/a`.
Install and uninstall into a project still require `-Path` (or the wizard prompt): guessing a
destination for a write is not worth the convenience.

**Completeness is a fixed definition, derived from the toolkit.** The `/code-audit` set is the items
named `code-audit` (skill, command) plus every agent in `toolkit/agents/`. The verdict per scope is
`complete`, `incomplete (missing: ...)` (some present) or `absent` (none). Hard-coding the name keeps
it simple; generalizing to arbitrary item groups is deferred until a second feature needs it.
"Present" means the item exists, not that it is up to date, since `differs` is already shown per item.

**Shadowing uses the existing hash comparison.** Where both scopes hold an item, compare their hashes:
equal is `both (same)`, unequal is `project shadows global (differs)`. This is the only combination
that changes behavior at run time, so it is the only one flagged loudly.

**Preflight mirrors what the hooks and command actually run.** Python is found as `python3` then
`python` (the agents' hook does `command -v python3 || command -v python`) and counts only if
`<it> --version` exits 0 and prints `Python 3.x`; this catches the Windows Store stub, which is found
on PATH but fails. The shell check looks for `bash` or `sh` on PATH, since the hooks are POSIX shell
and Claude Code on Windows runs them through Git Bash. Warn, never block.

**Smoke test = engine `--init` in a throwaway repo.** Create a temp dir, `git init`, write one file
(untracked files are in scope, so no commit or git identity is needed), run the installed
`audit.py --init` from there with the interpreter found in preflight, and require exit 0 and a JSON
line containing `evidence`. Always delete the temp dir, in `finally`. It runs against the engine in
the scope just written, project-first if both exist, matching the command's lookup. Alternatives:
`audit.py --help` (proves little: no git or scope logic) and a full phase 0/1 audit (slow, depends on
which scanners are installed). If the interpreter is unusable the smoke test is reported as skipped
with the preflight reason, not as passed.

**Exit codes carry the verdict.** The script exits 1 if verification fails (set incomplete after a
full install, or smoke test failed); warnings and `skipped` do not change the exit code. Needed so the
test script and CI-style callers can rely on it.

**Uninstall confirmation in flag mode** uses the existing yes/no prompt; `-Force` skips it. With no
interactive host the read fails and is treated as "no", so a scripted `-Uninstall` without `-Force`
removes nothing rather than hanging or deleting.

**Tests are one plain PowerShell script**, `toolkit/install/tests/Test-Installer.ps1`, with a tiny
assert helper, run as `powershell -File`, exit code non-zero on any failure. Each case builds a temp
`-ClaudeHome` and temp project folder and invokes the installer as a child process, asserting on
output text and resulting files. Alternative: Pester. Rejected for now: Windows PowerShell 5.1 ships
Pester 3, and requiring Pester 5 adds an install step for a small toolkit.

## Risks / Trade-offs

- [Hash-based matrix on large trees is slower: each item hashed in two scopes] → items are small
  (a handful of files); acceptable, and `differs` is only computed when both exist.
- [Smoke test could pass while Claude cannot use the install, e.g. hooks mis-resolve] → documented
  non-goal; the README keeps a manual "start a new session, run `/code-audit`" step.
- [`python3` first can pick the Store stub while `python` works] → preflight tests the same order the
  hook uses, so it warns about exactly the failure the hook would hit.
- [Parsing `git rev-parse` output from the current directory means `-List` behaves differently in
  different folders] → the header line states which project root, or `n/a`, was used.
- [Changing `-List` output breaks anything scraping it] → nothing in the repo does; noted in the
  proposal.

## Migration Plan

No data migration. Existing flags keep their meaning; the matrix replaces the single-scope `-List`
print. Rollback is reverting the script. The already-installed global copy of the toolkit is unaffected
by this change (the installer's own output changes, not the items it installs).
