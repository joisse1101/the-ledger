## 1. Verify the context-hiding flag

- [x] 1.1 (Done during exploration, 2026-10-15, user-run in a new session: the flagged namespaced command was absent from `/context`, the unflagged twin was listed, and the flagged one still ran when typed; throwaway files removed. Re-confirm quickly after the real commands are flagged.) On Claude Code 2.1.299, install a throwaway namespaced command with `disable-model-invocation: true` into `~/.claude/commands/` and start a new session; verify with `/context` that its description is not listed, that `/name` still runs, and that an unflagged twin is listed; record the result and, if the flag does not work, stop and revise design decision 9 and the `toolkit-skills` delta before continuing; remove both throwaway commands afterwards

## 2. Hide the existing commands and enforce it

- [x] 2.1 Add `disable-model-invocation: true` to the frontmatter of every file in `toolkit/commands/opsx/`
- [x] 2.2 Extend `api/check_docs.py` to fail, naming the file, when any `.md` under `toolkit/commands/` lacks the flag; add tests in `api/tests/test_check_docs.py` for a missing flag, a flagged file and a nested namespace file; run `cd api; pytest` and `python check_docs.py`
- [x] 2.3 (Done: `openspec update` writes the project `.claude/commands/opsx` and `.claude/skills/openspec-*`; the global install is untouched; design decision 10 revised.) Find out which folder `openspec update` writes (installed `~/.claude/commands/opsx` or somewhere else) on a copy or with the installed files backed up, and confirm whether it drops the flag; if the answer differs from design decision 10, revise that decision and the README text before continuing

## 3. Commit rule exception

- [x] 3.1 Add the `/jois:apply` exception line to `toolkit/rules/commit-hygiene.md` (run only, current branch, no amend, no push, no carry-over, not `/jois:stage`), paying for it by merging redundant bullets without losing a requirement of the approval section; bump `metadata.version` to `1.1.0` and `last_updated`; verify the file stays within the existing 2 KB budget, still has no `paths:`, and `python check_docs.py` passes (if it cannot fit, stop and decide on a budget change)

## 4. jois:apply

- [x] 4.1 Write `toolkit/commands/jois/apply.md` with `disable-model-invocation: true` and `metadata:`: change selection, status and instructions, context files, per-task implementation, checks (found from `CLAUDE.md`), split by concern, stage by explicit path, commit with the attribution line, branch creation when on the default branch, the stop conditions, the closing report, and a note naming `opsx:apply` as its origin
- [x] 4.2 Add `commands/jois/*.md` to `_versioned_items` in `api/check_docs.py` with a test for a missing version in a jois command and an exempt opsx command; run `pytest` and `python check_docs.py`
- [ ] 4.3 Verify end to end on a throwaway branch and a tiny two-task change: it commits each concern without a word, refuses to commit on a deliberately failing test, creates a branch when started on `main`, never pushes, and prints the commit report

## 5. jois:stage

- [x] 5.1 Write `toolkit/commands/jois/stage.md` with `disable-model-invocation: true` and `metadata:`: status analysis, concern selection and splitting, explicit-path staging, the plain-text presentation with a fresh word and turn end, the commit-on-word loop to a clean tree, change requests, and the skip list for unsafe files
- [x] 5.2 Specify and document the partial-file split in the command (`git apply --cached` with a prepared patch, else report and ask) and the pre-staged-changes handling
- [ ] 5.3 Verify on a scratch repo with a bug fix, a 10-file deletion, a rename, a lockfile change and an untracked `.env`: four commits one at a time with different words, `.env` reported as skipped, "looks good" refused, and a clean tree at the end

## 6. Installer and docs

- [x] 6.1 Confirm `Install-Toolkit.ps1` installs the `jois` namespace with `-Command jois` and lists it in `-List` without change; run it against a temp `-Scope project -Path`
- [x] 6.2 Update `toolkit/README.md`: the `jois` namespace, `/jois:apply` and `/jois:stage`, context hiding and the note that `openspec update` writes unflagged project copies (remove or re-flag them), and the opt-in `settings.json` snippets (`permissions.deny` for `git push*`, an `allow` list for git, tests, build and openspec)
- [ ] 6.3 Update `wiki/Coding-Standards.md` and `wiki/Repository-Layout.md` where they describe commit approval or the toolkit's commands; keep `CLAUDE.md` under 8 KB; run `cd api; python check_docs.py`

## 7. Finish

- [ ] 7.1 Run `cd api; pytest` and `python check_docs.py` and `openspec validate jois-commands`, all passing
- [ ] 7.2 Refresh the global install with `Install-Toolkit.ps1 -Force`, start a new session and verify `/context` lists none of the commands and `-List` shows every item up to date
