## 1. Docs check keeps the shared sections identical

- [x] 1.1 In `api/tests/test_check_docs.py` add tests: identical "PR body template" and "Author Verification" sections in `write-pr.md` and `update-pr.md` pass; a differing section fails and names both files; verify the new tests fail before the check exists (red) and pass after (`cd api; pytest tests/test_check_docs.py`)
- [x] 1.2 In `api/check_docs.py` add a check that extracts the H2 sections "PR body template" and "Author Verification" from both files and reports a mismatch naming both, skipped when either file is absent, and wire it into `check_toolkit`; verify `cd api; pytest tests/test_check_docs.py` passes

## 2. The command

- [x] 2.1 Create `toolkit/commands/jois/update-pr.md` with frontmatter (`name`, `description`, `disable-model-invocation: true`, `allowed-tools` for the git and gh commands it runs, the same merge-blocking PreToolUse hook as write-pr, `metadata.version` "1.0.0", `last_updated` the date of the change); verify `cd api; python check_docs.py` reports no frontmatter problem for it
- [x] 2.2 Write the Never list and the steps: find the PR (`gh pr list --head <branch> --state open`, none means point to `/jois:write-pr`), fetch, work out restack, push and refresh, present everything with one confirmation word and stop; verify each scenario of the "Update is confirmed" and "Manual-only PR update command" requirements has a matching sentence
- [x] 2.3 Write the restack step: the merged-base condition, `git rebase --onto origin/<default> <old-base> <branch>`, `git push --force-with-lease`, `gh pr edit <n> --base <default>`, abort on conflict, never delete the old base, closed-by-deleted-base case; verify every scenario of "Restack after the base PR merged" has a sentence and no step uses `--force` without `-with-lease`
- [x] 2.4 Write the push and refresh steps: plain `git push`, stop on a rejected push, regenerate the body, show a diff against the live body and name dropped text, keep the title unless asked or no longer fitting, write the body to a file outside the repo and run `gh pr edit --title`/`--body-file`; verify every scenario of "PR body is refreshed from the branch" has a sentence
- [x] 2.5 Copy the "PR body template" (with the ticking rules) and "Author Verification" sections from `write-pr.md` verbatim; verify `cd api; python check_docs.py` passes, which includes the new identical-sections check

## 3. Docs

- [x] 3.1 In `toolkit/README.md` add the `/jois:update-pr` entry: what it handles, the single confirmation word, plain push except an approved `--force-with-lease` restack, never merges, and the duplicated sections kept in step by the docs check; verify `cd api; python check_docs.py` passes
- [x] 3.2 Add `update-pr` to the `jois` list in `wiki/Repository-Layout.md`; verify `cd api; python check_docs.py` passes

## 4. Verification

- [x] 4.1 Run `openspec validate add-update-pr-command --strict` and verify it passes
- [x] 4.2 Smoke check only: install with `.\toolkit\install\Install-Toolkit.ps1 -Command jois -Force` from PowerShell, then run `/jois:update-pr` on a branch with no open PR and verify it loads, runs without error and, finding no PR, changes nothing and points to `/jois:write-pr` (result: run on `main` on 2026-10-19; it loaded, found `main` is the default branch, said there is no PR to update, pointed to `/jois:write-pr` and changed nothing). Whether restack, push and refresh behave as intended is left to UAT outside this change; no PR is created or edited
