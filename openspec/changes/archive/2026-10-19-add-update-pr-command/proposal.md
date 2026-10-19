## Why

After `/jois:write-pr` opens a PR, the work keeps moving: more commits land on the branch, the PR
body goes stale, and a stacked PR needs a restack once the PR under it merges. Today that is manual:
write-pr's final summary prints the restack commands for the user to type, and nothing refreshes a
body. A matching command closes the loop with the same safety posture.

## What Changes

- New manual-only command `/jois:update-pr` (`toolkit/commands/jois/update-pr.md`), for the open PR
  of the current branch. It finds the PR, then handles whichever of these apply, in order:
  1. **Restack**: the PR's base was a branch whose PR has merged and the base branch still exists.
     `git rebase --onto origin/<default> <old-base> <branch>`, `git push --force-with-lease`, then
     `gh pr edit --base <default>`.
  2. **Push**: commits on the branch that the remote head lacks, with a plain `git push`.
  3. **Refresh**: regenerate the body from the same template and Author Verification rules as
     write-pr, show a diff against the live body, and apply it with `gh pr edit --body-file`. The
     title changes only if the user asks or no longer fits the commits.
- One confirmation word covers everything it will do, shown first. It never merges (same hook), uses
  a plain push except the `--force-with-lease` of an approved restack, never renames a branch, and
  keeps the body out of shell text (file outside the repo).
- No open PR: it says so and points to `/jois:write-pr`. A PR that GitHub already closed because
  its base branch was deleted cannot be restacked; it says so and points to `/jois:write-pr`.
- The docs check (`api/check_docs.py`) fails if the "PR body template" and "Author Verification"
  sections differ between `write-pr.md` and `update-pr.md`, so the two commands cannot drift.
- Docs: `toolkit/README.md` and the `wiki/Repository-Layout.md` line.

Out of scope: addressing review comments (a later command), changing `write-pr`, merging, and
behavioral testing of restack, push and refresh, which is UAT done outside this change (no throwaway
PRs). This change verifies only that the command installs and runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-skills`: new requirements for the update command (existence and safety, restack, push,
  body refresh) and for the docs check that keeps the shared sections identical.

## Impact

- New `toolkit/commands/jois/update-pr.md` (with `metadata.version` and `last_updated`).
- `api/check_docs.py` and `api/tests/test_check_docs.py`.
- `openspec/specs/toolkit-skills/spec.md` via a delta; `toolkit/README.md`; `wiki/Repository-Layout.md`.
- The installer needs no change: it already copies every file under `toolkit/commands/jois/`.
- No change to the merge-blocking hook or to `write-pr.md`.
