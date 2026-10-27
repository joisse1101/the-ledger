## Context

`toolkit/commands/jois/write-pr.md` (2.2.0) holds the steps, guidelines, PR body template, ticking
rules and Author Verification rules in one file, and the spec requires it to be complete when copied
by hand. Its final summary prints the restack commands for the user to run. The installer copies every
entry under `toolkit/commands/` and `api/check_docs.py` requires `disable-model-invocation: true` and a
version on every `commands/jois/*.md` file. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- One command that brings an open PR up to date: restack, push, refresh the body.
- The body logic of write-pr and update-pr cannot drift apart.

**Non-Goals:**
- Handling review comments (later command), merging, creating PRs, renaming branches.
- Changing write-pr, its hook or its final summary.

## Decisions

**Duplicate the shared sections, enforce them with the docs check.** The PR body template, ticking
rules and Author Verification sections (about 130 lines) are copied into `update-pr.md`, and
`check_docs.py` fails when they differ from `write-pr.md`. Alternatives rejected:
- *Shared file under `commands/jois/`*: every `.md` there is a slash command, so it would appear as
  `/jois:<name>`, need the hidden flag and a version, and would not be copied by hand with a command.
- *Shared skill or rule*: breaks the write-pr requirement that the command is complete when copied
  by hand, and makes the commands depend on a third install.
- *Pointer ("read write-pr.md")*: fails when only one command is installed.
The check costs one function and two tests; the drift risk it removes is the main cost of duplicating.
The compared sections are the H2 sections "PR body template" and "Author Verification".

**One flow, three independent phases, one confirmation word.** Check, then read, then plan all that
applies, present it all, and stop. Phases: restack (only if its condition holds), push (only if the
remote head lacks commits), refresh (always compared; applied only if the body or title differs).
A single word authorizes the list shown, so the user never types a word before seeing the force push.

**Restack condition.** `gh pr view --json baseRefName,state,headRefName,body,title` gives the base. The
restack applies when the base is not the default branch, `gh pr list --head <base> --state merged`
shows a merged PR, and `git ls-remote --heads origin <base>` still finds the branch. Commands, from
write-pr's own summary: `git fetch`; `git rebase --onto origin/<default> <old-base> <branch>`; `git
push --force-with-lease`; `gh pr edit <n> --base <default>`. It never deletes the old base: the user
does after (write-pr's summary already says so). A conflict runs `git rebase --abort` and stops. If the
base branch is gone GitHub has closed the PR; `gh pr view` shows it CLOSED, and the command says it
cannot be reopened and points to write-pr.

**Force-with-lease is allowed only inside a confirmed restack.** A plain push is used otherwise; if it
is rejected as non-fast-forward the command reports it and stops instead of forcing. `--force` is
never used.

**Body refresh reuses write-pr's rules unchanged.** Same groups-free composition (one PR, so one
group): Changes Made from `git log origin/<base>..HEAD`, verification from `tasks.md`, chat runs and the
user. The live body is read with `gh pr view --json body`; the presentation shows a unified diff
(`git diff --no-index` on two scratch files, or inline comparison) and names dropped hand-written text.
The title stays unless the user asks or it no longer fits (a one-commit PR whose commit subject changed,
or commits added of another type); the squash merge uses the title as the commit message.

**Branch handling.** The command works on the current branch under its existing name and never
renames it. It ends on that branch. `allowed-tools`: the git read commands used by write-pr plus
`git rebase`, `git push` and `gh pr view`, `gh pr list`, `gh pr edit`; the same merge-blocking hook
as write-pr.

## Risks / Trade-offs

- [Duplicated text can drift] → the docs check fails the build; it compares only the two shared
  sections, so each command's steps can still change freely.
- [Force-with-lease rewrites the remote branch] → only in a restack the user confirmed after seeing
  it; the lease fails if someone else pushed.
- [A hand-edited live body is overwritten] → the diff names dropped text and nothing is applied
  until the word.
- [`gh pr list --state merged` may match an unrelated earlier PR from the same head] → the command also
  requires the base branch to still exist and the merged PR's base to be the default branch.

## Open Questions

- None that change the specs. The exact diff presentation (inline vs a scratch-file `git diff
  --no-index`) is decided during implementation.
