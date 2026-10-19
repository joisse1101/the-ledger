## Context

See proposal.md - Why. All three defects are in `toolkit/commands/jois/write-pr.md`: step 2 reads
`<base>..HEAD` with `<base>` the local branch name, step 8 passes the body with `--body-file -` on
stdin inside the shell command, and the final summary hard-codes `-s -d`. The `PreToolUse` hook
matches `gh\s+(pr\s+(merge|.*--auto)|api\b.*merge)` against the whole tool-input text, so any Bash call
whose text holds those words is refused.

Observed on this repo: a stale local `main` made `main..HEAD` list two merged commits; merging a PR
with `-d` closed the PR stacked on its branch, and GitHub refused both to retarget and to reopen it;
the hook refused a body that quoted its own message and an edit script that mentioned the words.

## Goals / Non-Goals

**Goals:**
- Group and size what the branch really adds, whatever state the local base branch is in.
- Never hand the user a merge command that closes a stacked PR.
- Let a PR body say anything, including the merge words, without weakening the merge ban.

**Non-Goals:**
- No change to the hook or its regex. A stricter-than-needed guard is accepted; a narrower matcher
  would let a hidden call (a variable, a wrapper) past the one thing the command must never do.
- No automation of the stack follow-up: the command still runs no merge, rebase or retarget itself.
- No change to the grouping rules, the template, the verification rules or the confirmation word.

## Decisions

**Remote base, not local.** Steps 2 and 8 use `origin/<base>`, after the `git fetch` already in step 2.
The alternative, fast-forwarding the local base, writes to the user's checkout and fails when the local
base has diverged. `origin/<base>` is read-only and always what the PR will be based on. If the ref is
missing the command stops and says so.

**Body from a file, written with the file-writing tool.** The hook cannot see file contents, only
command text, so a body in a file passes without touching the hook. The tool is the file-writing tool,
because writing the file from a shell command would put the same words in the command text. The path is
the session's scratch directory when the session names one, otherwise the OS temp directory; either is
outside the working tree, so it cannot be committed by accident. Not deleting the file is accepted: it
is temporary storage and removal would need another permission prompt. Rejected: narrowing the hook
(see Non-Goals) and keeping stdin with escaped words (brittle and still visible in the command text).

**Stack-aware merge commands.** A PR is "depended on" when another opened PR has its branch as base.
Those get `-s` with no `-d`. After it merges, for each later PR the summary lists, in order: rebase onto
the base branch (`git rebase --onto origin/<base> <earlier-branch> <branch>`, which needs the earlier
branch to still exist, hence no `-d`), push with `--force-with-lease`, `gh pr edit <n> --base <base>`,
then delete the earlier branch. Retargeting before the earlier PR merges was rejected: the diff would
include the earlier PR's commits until then, and a squash merge can still conflict. The last PR in a
stack keeps `-d`; it has nothing stacked on it.

**Version 2.1.0.** Behavior is corrected and one merge command changes, but the invocation is the same,
so a minor bump. `last_updated` is the date of the change.

**README states the hook's matching.** One sentence: the hook looks for the merge words anywhere in a
shell command's text, so text that merely mentions them is refused too, and the command passes PR
bodies from files for that reason.

## Risks / Trade-offs

- [The session names no scratch directory and the OS temp path is unusual] -> The command only needs an
  absolute path outside the working tree; failing to write stops before anything is pushed.
- [A user pastes a commit message with the merge words into a shell command] -> Still refused. Known,
  documented, accepted.
- [`git rebase --onto` fails because the earlier branch was deleted anyway] -> The summary says to
  merge without `-d`; if it was already deleted, the follow-up notes that the rebase point is the
  earlier branch's last commit.
- [The follow-up list is long] -> It appears only when a stack exists.

## Migration Plan

Reinstall with `Install-Toolkit.ps1 -Command jois -Force`. Rollback is reverting the commit.
