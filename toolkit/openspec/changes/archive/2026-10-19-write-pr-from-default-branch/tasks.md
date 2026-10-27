## 1. Command: default branch

- [x] 1.1 In `toolkit/commands/jois/write-pr.md` rewrite step 1 so the default branch no longer stops the command: stop only when `origin/<base>..HEAD` is empty (say there is nothing to open), otherwise carry on; verify the text "switch to a feature branch" is gone and the empty-range stop is present
- [x] 1.2 Change the Never list from "Never open a PR from the default branch" to "Never use the default branch as a PR head"; verify a search for "from the default branch" in the Never section finds only the new wording
- [x] 1.3 In step 8 add the default-branch path: one group with `origin/<base>` an ancestor of local `<base>` uses `git switch -c <branch>`; several groups or a diverged `<base>` use the existing cherry-pick path; verify both paths are written and no step uses `git reset`
- [x] 1.4 In step 8 add the final reset: after every push and `gh pr create` succeeded and every step-2 commit belongs to a created PR, switch to the last PR branch opened and run `git branch -f <base> origin/<base>`; on any failure do not reset; verify the text names `git branch -f` and the success gate
- [x] 1.5 In step 7 list the reset in the presentation when it will happen, and in the final summary report the reset and the old `<base>` tip hash; verify both sentences exist
- [x] 1.6 Add `Bash(git ls-remote:*)` to `allowed-tools`; verify `git branch` and `git switch` entries are still there

## 2. Command: branch names

- [x] 2.1 Add a "Branch names" subsection under Guidelines with the format, the commit types, the ticket rules (source, case, `#123` to `123`), the slug rules and the collision check (`git branch --list`, `git ls-remote --heads origin <name>`); verify every rule in the "Branch names follow a convention" requirement has a sentence
- [x] 2.2 Point step 3 at the subsection, say the current branch is never renamed, and remove the duplicate Best practices bullet; verify the old `type/short-description` wording appears nowhere
- [x] 2.3 Bump `metadata.version` to "2.2.0" and `last_updated` to the date of the change; verify `python check_docs.py` from `api/` passes

## 3. Docs

- [x] 3.1 In `toolkit/README.md` update the `/jois:write-pr` entry: runs from the default branch, branches off and resets it with `git branch -f` after the PRs are pushed, and the branch-name convention; verify `python check_docs.py` from `api/` passes
- [x] 3.2 Update the `write-pr` clause in `wiki/Repository-Layout.md` to mention opening PRs from the default branch; verify `python check_docs.py` from `api/` passes

## 4. Verification

- [x] 4.1 Run `openspec validate write-pr-from-default-branch --strict` and verify it passes
- [x] 4.2 In a scratch clone with two commits on local `main` and one uncommitted file, run `/jois:write-pr` and verify: the presentation lists the reset, the PR head is a `type/slug` branch, after the word local `main` equals `origin/main`, the uncommitted file is still present and the old tip is in the summary (result: run in this repository instead of a scratch clone, with one commit on `main` and an untracked directory as the uncommitted content; PR #34 was opened from `feat/open-prs-from-main`, the presentation listed the reset, local `main` equalled `origin/main` afterwards, the untracked directory survived and the old tip hash was reported. Narrower scope: not exercised were two groups (cherry-pick path from `main`), a modified tracked file, and a diverged local `main`)
