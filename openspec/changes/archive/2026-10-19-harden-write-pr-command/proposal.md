## Why

Using `/jois:write-pr` on this repo exposed three defects. It reads the branch's commits against the
local `main`, which was behind the remote, so it listed two already-merged commits as part of the
branch. Its merge-order summary recommends `gh pr merge <n> -s -d` for every PR, and deleting the
branch of a PR that another PR is based on makes GitHub close the second PR, which can then be neither
retargeted nor reopened. And a PR body that quotes the merge-blocking hook's message was refused,
because the hook matches the merge words anywhere in a Bash command's text and the body was passed
inside the command.

## What Changes

- Compare against the remote base branch (`origin/<base>`) when reading commits and diffs, and when
  creating each group's branch. The command already runs `git fetch`; a stale local base no longer
  changes what it sees.
- Pass each PR body to `gh pr create` from a temporary file outside the repository, written with the
  file-writing tool, instead of inline on stdin. A body that contains the merge words is no longer
  blocked. The hook itself is unchanged and stays strict, so any other Bash text with those words is
  still refused.
- Change the merge-order summary for stacked PRs. A PR that another PR is based on is given
  `gh pr merge <n> -s` without `-d`, and the summary lists the follow-up for the later PR in order:
  rebase it onto the base branch, push with `--force-with-lease`, retarget it to the base branch, then
  delete the earlier branch. Independent PRs and the last PR in a stack keep `-s -d`.
- Document the hook's exact matching in `toolkit/README.md` so the limit is known.
- Bump `/jois:write-pr` to 2.1.0.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-skills`: "PRs grouped by concern and confirmed" reads the remote base; "Merge-order summary"
  gives stack-aware merge commands; a new requirement covers passing the PR body from a file.

## Impact

- `toolkit/commands/jois/write-pr.md` (steps 2 and 8, final summary, version) and `toolkit/README.md`.
- No change to `api/check_docs.py`, the installer or the hook script.
- Installed copies update with `Install-Toolkit.ps1 -Command jois -Force`.
