## Why

Opening PRs by hand means retyping the same template, re-reading the branch to list commits, and
deciding each time whether a branch is too big for one PR. Past PRs (#20-#24) were one branch each,
some with about 30 commits. A skill can do the mechanical part and keep the discipline the PR
guidelines ask for: small single-concern PRs, conventional titles, a body that explains why, and a
human who does every merge.

## What Changes

- Add a manual-only skill `toolkit/skills/write-pr/` (`disable-model-invocation: true`, run as
  `/write-pr`) that turns the commits on the current branch into one or more GitHub PRs.
- It groups commits by concern, shows the grouping, and waits for the user to confirm it.
- For each group it builds a conventional-commit title and fills the PR template: summary (why),
  type of change ticked from commit types, changes made from `git log`, and tests.
- Tests section: lists the test files and tests the group adds or changes (assumed run), and takes
  manual steps and results from the OpenSpec change's `tasks.md` when one exists. There is no
  visual-proof section. "Related Issues" is left out when there are none.
- It blocks on secrets or `.env` files in the diff and warns on debug prints and oversized groups.
- It pushes and runs `gh pr create` only after the user types a confirmation word.
- It never merges. A skill-scoped `PreToolUse` hook blocks `gh pr merge` once the skill is invoked.
- It ends with a list of every PR it opened, in merge order, with the `gh pr merge <n> -s -d`
  command for each, for the user to run.
- Package the template and the PR guidelines as support files inside the skill folder.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-skills`: adds the requirements for the PR skill (grouping, confirmation gate, never
  merging, final merge-order summary, self-contained folder).

## Impact

- New: `toolkit/skills/write-pr/SKILL.md` (with the inline merge-guard hook) and the PR template and
  guidelines as support files.
- Updated: `toolkit/README.md` (skills section), the matching `wiki/` page, `openspec/specs/toolkit-skills`.
- `python check_docs.py` must pass: version block, size budgets, links.
- No change to the installer; a skill folder is already a unit it installs.
- Not included: a repo-wide deny rule for `gh pr merge` (a user settings change, done separately).
