## 1. Test harness first

- [ ] 1.1 Create `toolkit/install/tests/Test-Installer.ps1` with an assert helper, a per-case temp `-ClaudeHome` plus temp project folder, and a child-process runner for the installer; verify `powershell -File` on it with zero cases exits 0 and a deliberately failing case exits non-zero
- [ ] 1.2 Add cases that pin today's behavior (fresh install, idempotent re-run, `differs` skipped without `-Force` and overwritten with it, uninstall leaves foreign items, unknown name and unknown target errors) and verify they fail only for the global ones until `-ClaudeHome` exists

## 2. Sandboxable destinations

- [ ] 2.1 Add `-ClaudeHome <dir>` to `Install-Skills.ps1` and make global destinations resolve under it (default `$HOME\.claude`); verify a global install with `-ClaudeHome $env:TEMP\x` writes only there and the real `~/.claude` hashes are unchanged
- [ ] 2.2 Refactor destination and state helpers to take scope, project root and claude home as parameters instead of reading script-level state; verify the 1.2 cases still pass

## 3. Status matrix and completeness

- [ ] 3.1 Resolve the project root for read-only views (`-Path`, else `git rev-parse --show-toplevel`, else `n/a`) and print which was used; verify with cases run from inside and outside a git repo
- [ ] 3.2 Replace the single-scope `-List` print and the wizard "Check" with the global/project matrix including `both (same)` and `project shadows global (differs)`; verify cases for each combination of missing, up to date and differs across the two scopes
- [ ] 3.3 Add the per-scope `/code-audit` verdict (`complete`, `incomplete (missing: ...)`, `absent`) and show it under the matrix; verify with a case that removes one agent and expects the name in the output
- [ ] 3.4 Make the wizard warn when a partial pick would leave the set incomplete; verify by reading the prompt path manually with a piped answer or a documented manual check

## 4. Preflight and verify

- [ ] 4.1 Add the preflight (git, `python3` then `python` that prints `Python 3.x` and exits 0, `bash` or `sh`) printing warnings only; verify by running with a PATH that hides each tool in turn and confirming a warning and a continued install
- [ ] 4.2 Add the engine smoke test (temp repo, one untracked file, installed `audit.py --init`, require exit 0 and a JSON line with `evidence`, delete the temp dir in `finally`); verify it passes on a healthy sandbox install, fails when `audit.py` is broken, and leaves no temp directory behind either way
- [ ] 4.3 Run the completeness check plus smoke test after every install, report `skipped` when Python is unusable, and exit 1 on failure; verify exit codes for healthy, incomplete and broken-engine installs
- [ ] 4.4 Replace the wizard-only closing hints with a summary for every install (scope, installed/updated/skipped/unchanged counts, verify result, restart note, and the commit-or-ignore note for project scope); verify output in a global and a project case

## 5. Safer uninstall

- [ ] 5.1 Ask for confirmation on flag-mode `-Uninstall` unless `-Force`, treating an unreadable prompt as "no"; verify a piped `n` and a non-interactive run remove nothing, and `-Force` removes only toolkit items

## 6. Docs and final check

- [ ] 6.1 Update `toolkit/README.md` (matrix, `-ClaudeHome`, verify and summary, how to run the test script, the manual new-session step) and the toolkit paragraph in `wiki/Repository-Layout.md`; verify `cd api; python check_docs.py` passes
- [ ] 6.2 Run the full test script, then `openspec validate refine-toolkit-installer --strict`; verify both pass
- [ ] 6.3 Manual end-to-end per the earlier walkthrough: sandbox install, matrix, then real global install, a new Claude Code session, `/code-audit`, and inspect `code-audit/<run>/` for both agent JSONs and a merged `report.md`; record anything broken as follow-up tasks rather than fixing silently
