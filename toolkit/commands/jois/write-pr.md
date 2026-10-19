---
name: "JOIS: Write PR"
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
  version: "2.0.0"
  last_updated: "2026-10-19"
---

# Write PRs

Turn the commits on this branch into one or more PRs. The rules are in the sections below this
list of steps: Guidelines, PR body template and Author Verification.

## Never

- Never merge: no `gh pr merge`, no `--auto`, no auto-merge, no merge through `gh api`. A hook
  blocks it. The user merges.
- Never push or create anything before the user types the confirmation word. Never force-push.
- Never open a PR from the default branch.
- Never run a command the user has not agreed to, and never edit code to make a run pass.

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
5. **Gather verification** for every group as Author Verification below says: `tasks.md`, runs seen
   in this conversation, then the offer to run missing tests. If a question is needed, ask it once for
   all groups, in plain text, and end the turn. Continue from the reply.
6. **Compose** each PR from the PR body template:
   - Title: the commit subject for a one-commit group; otherwise a new `type(scope): subject`
     (lowercase, imperative, no period). The squash merge makes it the commit on the base.
   - Summary leads with why. Related Issues only from `#n` or ticket ids in commit messages or the
     branch name; otherwise omit the section.
   - Changes Made: the group's commit subjects from `git log`.
   - Tests: test files the group adds or changes, and their names. Fill Author Verification and How
     to Test This PR as the Author Verification section says. Never state a result no source records.
   - End with the PR attribution line the session gives, if any.
7. **Present and stop.** Show the groups with their commits, then for each PR the title, base, head,
   body, size, and any warning or block, including any run reported as failed, timed out or out of
   date. Tag each verification bullet and reviewer step with its source (Author Verification, Sources).
   Name a common confirmation word that differs from your previous prompt's and say: "Reply with
   <word> to open these PRs, or tell me what to change." Then end the turn and call no tool. "Yes" or
   "looks good" is not the word. After any change request, present again with a new word.
8. **Open** after the word, one group at a time, in dependency order:
   - A group that is not the only one: `git switch -c <branch> <base>`, then `git cherry-pick` its
     commits in order. On a conflict, run `git cherry-pick --abort`, retry on the branch of the group
     it depends on, and base that PR on that branch.
   - `git push -u origin <branch>`, then `gh pr create --base <base> --head <branch> --title "<title>"
     --body-file -` with the body on stdin, without the source tags. Record the number and URL.
   - Return to the original branch when done.
9. **Summarize** (below).

## Final summary

List every PR opened: number, title, URL and base, in the order to merge. Dependent PRs come in
stack order; independent ones are marked "any order". Give each as `gh pr merge <n> -s -d` for
the user to run, and run none. For a PR based on another PR's branch, add: after the earlier PR
merges, run `git rebase --onto <base> <earlier-branch> <branch>` and push with `--force-with-lease`.
If no PR was opened, say so and why.

## Guidelines

Read this while grouping commits and writing titles and bodies.

### Rule 1: Keep scope small and focused

- A PR solves one issue or implements one feature.
- Aim for under 200-400 changed lines. Large PRs are hard to review and prone to bugs. Past about
  300 lines review quality drops sharply, so split into stacked or smaller PRs.
- Never combine refactoring or formatting with new feature logic in one PR.

### Rule 2: Descriptive titles and summaries

- Title in Conventional Commits form, lowercase and imperative, no trailing period:
  `feat(auth): add oauth2 authentication flow`, `fix(cart): prevent negative item quantity on checkout`.
- Explain why the change was made. The diff already shows what changed.

### Rule 3: Self-review and verification

- Check the diff for accidental files (logs, `.env`, temp files) and debug output before opening.
- Say which tests were added or run, and whether manual testing was done.

### Rule 4: Clean commit history

- No vague commits (`fix bug`, `updates`, `wip`). Each commit is a logically complete step.
- Squash fixups and temporary commits before review.

### Hard rules

- Automated CI (formatting, lint, static analysis, type checks, tests) must pass; a PR with failing
  tests cannot merge.
- Never commit API keys, `.env` files, credentials, build artifacts or system files such as `.DS_Store`.
- One logical unit of work per PR. Refactoring and a new feature go in separate PRs.
- No direct commits to `main` or production branches: every change goes through a feature or bugfix
  branch and a PR with at least one human approval.

### Best practices

- Branch names are `type/short-description` (`feat/add-user-auth`, `fix/checkout-crash`).
- Read your own diff on the platform before asking for review: debug logging, commented-out code,
  unintended files.
- Give the reasoning behind architectural decisions in the description.

## PR body template

Fill every section below, then delete the `<!-- -->` comments before opening the PR. Keep the
emoji headings exactly as written.

```markdown
## 📌 Summary
<!-- What this PR does and why it is needed. Lead with the why; the diff already shows the what. -->

## 🔗 Related Issues / Tickets
<!-- OMIT THIS WHOLE SECTION unless a commit message or the branch name references an issue or ticket
     (Closes #123, Fixes PROJ-456). Never invent one. -->

## 🛠 Type of Change
- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 💥 Breaking change (fix or feature causing existing functionality to fail)
- [ ] ♻️ Refactoring / Technical Debt (no logical/functional changes)
- [ ] 📚 Documentation / Comments
- [ ] 🧪 Tests (adding missing or updated tests)

## 📝 Changes Made
<!-- One bullet per commit in this PR: the commit subject, copied from `git log`. -->
-

## 🧪 How Has This Been Tested?
<!-- List the tests this PR adds or changes under the first box. -->
- [ ] Automated Unit / Integration Tests passed
- [ ] Manual testing completed

### Author Verification
<!-- What the author ran and saw, one bullet per check. Never state a result no source records. -->
- **Label:** command or input, then the observed result

### How to Test This PR
<!-- Steps for a reviewer, numbered, each command in a fenced block. See Author Verification. -->
1. Fetch and check out this branch.
```

### Ticking rules

- **Type of Change**: `feat` ticks New feature; `fix` ticks Bug fix; `refactor`, `perf` and `style`
  tick Refactoring; `docs` ticks Documentation; `test` ticks Tests. A `chore` group touching only docs
  or specs ticks Documentation, otherwise nothing. Tick Breaking change when any commit subject has
  `!` after the type or any commit body has a `BREAKING CHANGE` footer. Several boxes may be ticked.
- **Automated**: tick when the group adds or changes a test file, and list those files and the test
  names under the box. The user has said to assume the tests were run.
- **Author Verification**: bullets come from the matching OpenSpec `tasks.md`, runs seen in this
  conversation and, where neither has any, the user's answer; the Author Verification section says
  how. A bullet reports no result its source lacks. Quote a count only when a source records it. With
  no bullets, write `- None recorded.`
- **Manual**: tick only when at least one Author Verification bullet is a manual check: a command run
  or behavior observed by hand, not the repository's test command. Otherwise leave it unticked.
- **How to Test This PR**: steps follow the Author Verification section. Delete the subsection if none
  survive.
- No visual-proof section. Do not add one.

## Author Verification

How to fill the two testing subsections of the template. Sources are read, not guessed: only the
runs the user agrees to are executed (Missing verification).

### Sources of a bullet

Find the OpenSpec change whose files the group's commits touch, in `openspec/changes/<name>/` or
`openspec/changes/archive/*-<name>/`, and read its `tasks.md`. Sort each task by its text:

| Task | Bullet |
|---|---|
| Checked, asks to verify, dry-run or run something, and records the outcome (a `(result: ...)` clause or the outcome in the text) | The check and the recorded result. Source `tasks.md N.N, result recorded`. |
| Checked, asks to verify, but records no outcome | The check only, no outcome. Source `tasks.md N.N, no result recorded`. |
| Unchecked, or plain work with nothing to verify | None. |

Then read this conversation for **runs**: a test, build, type-check or lint command with its output
visible, run by Claude or by the user (`!`). Each yields a bullet with source `chat`, under these rules:

- A run covers a group only if its directory or paths include a directory the group's diff changes;
  a run at the repository root covers every group.
- State only the outcome and counts the output shows. Infer nothing from the command alone.
- The latest run of a command is the one that counts. If it failed, tell the user it failed and write
  no passing bullet. If an Edit or Write in the conversation touched a file in the group's diff after
  the run, tell the user the run is out of date and write no bullet for it.
- A summarized history, or a session with no runs, contributes nothing. Never reconstruct a run you
  cannot see.
- A `chat` bullet and a `tasks.md` bullet can both appear: they record different runs.

Never add a result a source lacks. Quote a count (tests passed, files copied) only when the source
gives it. A bullet is **manual** when it is a command run or behavior seen by hand; running the
repository's test command is automated.

### Missing verification

A group has none when no source above gives a bullet with a result: no OpenSpec change, no verification
task in `tasks.md`, a task with no recorded result, and no usable run. For these groups:

1. **Offer to run.** Pick, per group, a command a repository document states (`CLAUDE.md`, README,
   `package.json` scripts, a testing page) for a directory the group's diff changes, copied as written
   with no added flags. Every script and path in it must exist in the checkout; drop it if one does
   not. Do not invent a command.
2. **Ask once, for all groups, in plain text, then end the turn.** Name each offered command and the
   directory it runs in, and say it runs on the checked-out branch tip, including uncommitted changes.
   For a group with no documented command, ask what they ran and saw instead. Say that declining an
   offer means telling you what they ran, or that none was run. Run nothing before the reply.
3. **After the reply**, run only the commands the user agreed to, each through the normal permission
   prompt. A passing run becomes a `chat` bullet with the command and the counts its output shows.
   Report a failing, unreadable or timed-out run to the user: no passing bullet, no attempt to fix it,
   and the PR is not blocked. Turn any user-stated results into bullets with source `user`, and add
   nothing the reply did not say. If the user ran nothing, write `- None recorded.` and leave Manual
   unticked.

### How to Test This PR

Suggest steps from the group's diff, its `tasks.md` and the repository's own documents. Keep a step
only if it is one of:

1. **Checkout**: `git fetch`, then `git switch <branch>`. Always first.
2. **Run**: a command a document states, for a directory the diff changed, copied as written with no
   added flags. Check that every script and path in it exists in the checkout; drop the step if one does
   not. Do not repair it.
3. **Read**: a file in the diff and why to start there. A script no document explains gets a read step
   at most, never a run step.

Never invent a command or flag. Put each command in a fenced block. Delete the subsection if only the
checkout step is left and the diff has nothing worth reading first.

### Sources

When presenting a PR, tag every bullet and step: `tasks.md N.N, result recorded`,
`tasks.md N.N, no result recorded`, `chat`, `repo docs`, `inferred from diff` (a read step, or a run
step chosen among documented commands) or `user`. The author reviews the draft and the tags show where
to look first. Strip every tag from the body passed to `gh pr create`.
