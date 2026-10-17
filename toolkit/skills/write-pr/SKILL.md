---
name: write-pr
description: Open GitHub pull requests for the commits on the current branch, grouped by concern, from the team template. Manual only; never merges.
disable-model-invocation: true
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git log:*), Bash(git diff:*), Bash(git fetch:*), Bash(git switch:*), Bash(git cherry-pick:*), Bash(git push:*), Bash(gh repo view:*), Bash(gh pr list:*), Bash(gh pr create:*)
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: >-
            powershell -NoProfile -Command "if ([Console]::In.ReadToEnd() -match 'gh\s+(pr\s+(merge|.*--auto)|api\b.*merge)') { [Console]::Error.WriteLine('write-pr never merges: the user runs gh pr merge'); exit 2 }"
metadata:
  version: "1.1.0"
  last_updated: "2026-10-18"
---

# Write PRs

Turn the commits on this branch into one or more PRs. Read `guidelines.md` for the rules,
`pr-template.md` for the body and ticking rules, and `verification.md` for the testing section, all
next to this file.

## Never

- Never merge: no `gh pr merge`, no `--auto`, no auto-merge, no merge through `gh api`. A hook
  blocks it. The user merges.
- Never push or create anything before the user types the confirmation word. Never force-push.
- Never open a PR from the default branch.

## Steps

1. **Check.** `git branch --show-current` and the base from `gh repo view --json defaultBranchRef
   -q .defaultBranchRef.name`. On the base branch, stop and say to switch to a feature branch. If
   `gh pr list --head <branch> --state open` shows a PR, report it and stop. Note uncommitted changes
   (`git status --short`); they are not in any PR.
2. **Read.** `git fetch`, then `git log --reverse --format="%h %s" <base>..HEAD` and `git diff
   --numstat <base>...HEAD`. No commits: say so and stop.
3. **Group by concern.** One group per logical unit of work. Refactors never share a group with
   features. Test, docs and OpenSpec archive commits join the group they describe; they form their own
   group only when the whole branch is that kind of change. Flag a group over about 400 changed lines.
   Name each group's branch `type/short-description`; one group uses the current branch.
4. **Scan each group's added lines.** Block that group, naming the file, on a secret or credential, an
   `.env*` file, `*.pem`/`*.key`, or build output. Warn, without blocking, on `console.log`, `print` or
   `debugger` calls and commented-out code.
5. **Compose** each PR from `pr-template.md`:
   - Title: the commit subject for a one-commit group; otherwise a new `type(scope): subject`
     (lowercase, imperative, no period). The squash merge makes it the commit on the base.
   - Summary leads with why. Related Issues only from `#n` or ticket ids in commit messages or the
     branch name; otherwise omit the section.
   - Changes Made: the group's commit subjects from `git log`.
   - Tests: test files the group adds or changes, and their names. Fill Author Verification and How
     to Test This PR as `verification.md` says. Find the OpenSpec change whose files the group's
     commits touch, in `openspec/changes/<name>/` or `openspec/changes/archive/*-<name>/`, and read
     its `tasks.md`. Never state a result no source records.
   - If any group lacks verification, ask the user once for all of them, in plain text, and end the
     turn. Compose from the reply, then continue to step 6.
   - End with the PR attribution line the session gives, if any.
6. **Present and stop.** Show the groups with their commits, then for each PR the title, base, head,
   body, size, and any warning or block. Tag each verification bullet and reviewer step with its
   source (`verification.md`). Name a common confirmation word that differs from your
   previous prompt's and say: "Reply with <word> to open these PRs, or tell me what to change."
   Then end the turn and call no tool. "Yes" or "looks good" is not the word. After any change
   request, present again with a new word.
7. **Open** after the word, one group at a time, in dependency order:
   - A group that is not the only one: `git switch -c <branch> <base>`, then `git cherry-pick` its
     commits in order. On a conflict, run `git cherry-pick --abort`, retry on the branch of the group
     it depends on, and base that PR on that branch.
   - `git push -u origin <branch>`, then `gh pr create --base <base> --head <branch> --title "<title>"
     --body-file -` with the body on stdin, without the source tags. Record the number and URL.
   - Return to the original branch when done.
8. **Summarize** (below).

## Final summary

List every PR opened: number, title, URL and base, in the order to merge. Dependent PRs come in
stack order; independent ones are marked "any order". Give each as `gh pr merge <n> -s -d` for
the user to run, and run none. For a PR based on another PR's branch, add: after the earlier PR
merges, run `git rebase --onto <base> <earlier-branch> <branch>` and push with `--force-with-lease`.
If no PR was opened, say so and why.
