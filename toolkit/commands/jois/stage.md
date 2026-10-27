---
name: "JOIS: Stage"
description: "Clear a messy working tree one concern at a time: stage, propose a message, wait for a confirmation word, commit, repeat until clean"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git restore --staged:*), Bash(git apply --cached:*), Bash(git commit:*)
disable-model-invocation: true
metadata:
  version: "1.0.1"
  last_updated: "2026-10-27"
---

<!-- The pause below follows the commit block of the generated `commands/opsx/apply.md`, in a loop.
Re-sync by hand if that block changes. This command has NO commit authority of its own:
every commit waits for the user's confirmation word. -->

Clear a messy working tree in clean single-concern commits, each confirmed by the user. This does
not need an OpenSpec change. Follow the commit-hygiene rule throughout.

## Limits

- Never commit without the user typing the word from your most recent prompt. "Yes", "looks good"
  or "continue" is not the word. No `--amend`. No push, reset, rebase, stash or clean.
- Never `git add .`, `git add -A` or `git commit -a`. Stage by explicit path.
- Never commit while the build, type-check or tests fail, unless the commit is the fix. Find the
  commands in `CLAUDE.md` or the project config and run them before presenting a concern; if none
  can be found, say so and present anyway, noting the changes are unchecked.

## Each turn (the loop)

1. **Read the tree**: `git status --short` and the diffs (`git diff`, `git diff --staged`; read
   untracked files that are not obviously unsafe). Changes already staged belong to the analysis:
   say so, and unstage with `git restore --staged <path>` anything that mixes concerns.
2. **Skip unsafe files**: never stage secret files (`.env*`, `*.pem`, `*.key`, credentials) or build
   output (`node_modules`, `dist`, `build`, `__pycache__`, `*.log`, caches) that are not
   gitignored. Name each as skipped, with a suggestion to gitignore it. Skipped files do not
   count against a clean tree.
3. **Pick the first concern.** A concern is what the change does, not a file count. Deletions, a
   rename or move, a regenerated or binary asset, a lockfile and a format-only change are each one
   concern however many files, and never share a commit with a behavior change. Split a
   hand-written change over about 200 lines or 5 files, or spanning more than one layer. Tests,
   specs and docs ship with the change they describe.
4. **Stage it by explicit path** (`git add <path>`). If one file holds two concerns, split it
   (below).
5. **Verify**: run the checks from the Limits section. If they fail and this concern is not the
   fix, do not present it; report the failure and stop.
6. **Present and end the turn.** Run `git diff --staged --stat`, then print as plain text, not in a
   question tool: the staged file summary, the proposed message (`type(scope): subject`, type feat,
   fix, refactor, perf, style, docs, test, build, ci, chore or revert, lowercase imperative subject with no trailing period,
   the session's `Co-Authored-By` line last), the list of concerns still waiting, and the skipped
   files. Name a common confirmation word that differs from the word in your previous prompt, and
   say: "Staged. Reply with <word> to commit, or tell me what to change."
   **Then end the turn. Do not call AskUserQuestion or any other tool, and do not run `git commit`.**

## When the user replies

- **The current word**: run `git commit` with exactly the proposed message, record the short hash,
  then go back to step 1 in the same turn for the next concern.
- **A request for changes**: edit, restage, present again with a new word, end the turn.
- **Anything else**, including "yes" or approval of the work, or an earlier word: do not commit;
  restate the current word.

## Splitting a file that holds two concerns

`git add -p` does not work here. Write the wanted hunks to a patch file (from `git diff -- <path>`,
keeping only the hunks of this concern, with their headers and correct line counts), check it with
`git apply --cached --check <patch>`, then `git apply --cached <patch>` and delete the patch file.
If a clean patch cannot be built (hunks overlap, or the lines are interleaved), do not guess:
report the file, name the two concerns, and ask the user to split the edit.

## Done

When `git status` shows no changes except skipped files, print the commits made (short hash and
message), name the skipped files, and stop.
