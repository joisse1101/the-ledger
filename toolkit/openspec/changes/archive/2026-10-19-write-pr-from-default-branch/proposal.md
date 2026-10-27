## Why

`/jois:write-pr` stops when the current branch is the default branch, yet that is where commits
often end up: work is committed on `main`, then needs a PR. The user has to branch and reset `main`
by hand first. The command also names branches only as `type/short-description`, which leaves
ticket ids, casing and collisions to chance.

## What Changes

- On the default branch with local commits ahead of `origin/<base>`, the command no longer stops. It
  groups those commits as usual and opens the PRs from new branches: `git switch -c` for a single
  group, cherry-pick onto `origin/<base>` for several.
- After every PR is pushed and created, it resets local `<base>` with `git branch -f <base>
  origin/<base>`, never `git reset --hard`, so uncommitted changes survive. It ends on a branch
  other than the default branch. The confirmation-word presentation lists the reset.
- "Never open a PR from the default branch" becomes "never use the default branch as a PR head".
- New branch-name rules: `<type>/<ticket>-<slug>` when a commit message or the branch name
  references a ticket, else `<type>/<slug>`. The type is a commit type (`feat`, `fix`, `refactor`,
  `style`, `docs`, `test`, `chore`). The slug is lowercase kebab-case, 2 to 4 words, imperative, never a
  bare `fix`, `update` or `test`. The ticket keeps its tracker case (`PROJ-123`; GitHub `#123`
  becomes `123`) and is never invented. A name that exists locally or on `origin` is not reused: the
  command proposes another. The current branch is never renamed.
- Docs follow: `toolkit/README.md` and the `wiki/Repository-Layout.md` line.

Out of scope: the `update-pr` command (a later change).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-skills`: the "Manual-only PR skill" requirement no longer refuses the default branch; the
  "Confirmation before publishing" requirement covers the reset; a new requirement covers branch
  names and one covers the reset of the default branch.

## Impact

- `toolkit/commands/jois/write-pr.md`: steps 1, 3, 7 and 8, the Never list, Best practices; version
  and `last_updated` bump. `allowed-tools` already holds `git branch:*` and `git switch:*`.
- `openspec/specs/toolkit-skills/spec.md` via a delta.
- `toolkit/README.md`, `wiki/Repository-Layout.md`.
- No change to the merge-blocking hook or to code outside the toolkit.
