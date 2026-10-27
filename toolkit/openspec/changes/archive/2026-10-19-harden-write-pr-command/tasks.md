## 1. Command fixes

- [x] 1.1 In `toolkit/commands/jois/write-pr.md` change step 2 to read `origin/<base>..HEAD` and `origin/<base>...HEAD`, stop when `origin/<base>` is missing, and change step 8 to cut each group's branch from `origin/<base>`; verify a search for `<base>..HEAD` and `-c <branch> <base>` finds nothing and `origin/<base>` appears in steps 2 and 8
- [x] 1.2 Change step 8 and the Never section so each body is written without source tags to a temporary file outside the repository with the file-writing tool and passed as `--body-file <path>`, never inline; verify a search for `--body-file -` and "stdin" finds nothing in the file
- [x] 1.3 Rewrite the Final summary: `-s -d` for a PR nothing is based on, `-s` without `-d` for a PR another PR is based on, and for each later PR the ordered rebase, `--force-with-lease` push, `gh pr edit <n> --base <base>` and earlier-branch deletion; verify each scenario of "Merge-order summary" has a matching sentence
- [x] 1.4 Bump `metadata.version` to "2.1.0" and `last_updated` to the date of the change; verify `python check_docs.py` from `api/` passes

## 2. Docs

- [x] 2.1 In `toolkit/README.md` update the `/jois:write-pr` entry: stack-aware merge commands, bodies passed from files, base read from the remote, and one sentence that the hook matches the merge words anywhere in a shell command's text; verify `python check_docs.py` from `api/` passes

## 3. Verification

- [x] 3.1 Run `openspec validate harden-write-pr-command --strict` and verify it passes (result: change is valid)
- [x] 3.2 Open a PR through the command whose body contains `gh pr merge` and verify it is created and a shell command containing those words is still refused (result: PR #32 was created from a body quoting `gh pr merge <n> -s -d`; earlier in the same session a shell command containing those words was refused)
