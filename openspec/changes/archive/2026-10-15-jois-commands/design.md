## Context

See proposal.md for motivation. Current state: `toolkit/commands/opsx/*.md` are OpenSpec-generated
copies; `opsx:apply` stops after each concern for a confirmation word (commit-hygiene, unscoped,
1.0.0, 2023 of 2048 bytes). Slash commands are loaded as skills, so each installed command's
description sits in every new session (about 300 tokens for the user's commands, from `/context`).
`api/check_docs.py` validates rule budgets and versions; the in-progress `review-tracking` change
also edits that file and plans a `jois-review` command namespace. This change must not read, edit
or depend on `review-tracking`.

## Goals / Non-Goals

**Goals:**
- Run an OpenSpec change to completion in the user's session with commits made unattended and
  safely bounded.
- Clear a messy working tree in clean single-concern commits, with the user confirming each.
- Keep command descriptions out of new sessions' context.

**Non-Goals:**
- `jois:review`, `jois-review:*` or anything from `review-tracking`.
- A background or sub-agent apply (rejected below).
- Hiding skills, the claude.ai sync skills, built-in skills or project skills.
- Editing `settings.json` from the installer.
- Changing `opsx:apply`, which keeps its confirmation stop.

## Decisions

**1. `jois:apply` is a main-thread command, not an agent.** The user wants to watch it and not
micromanage it. A background agent cannot ask a question, so on an ambiguous task it could only
stop and report after the fact, and permission prompts could stall it unseen. In the main thread
the stop conditions (ambiguity, scope, design flaw, red checks, blocker, interruption) stay
interactive. *Alternative:* a launcher plus a `jois-applier` agent for isolated context; deferred
as a later variant if long runs prove too heavy for the session (1M window, auto-compaction).

**2. Authority is the invocation, written into the rule.** The unscoped `commit-hygiene` rule
loads in every session and would otherwise block the unattended commits, so the command text alone
cannot override it. The rule gains one exception sentence: a run of `/jois:apply` started by the
user authorizes commits for that run only, on the current branch, no `--amend`, no push, and does
not carry to later commands or sessions. `/jois:stage` is deliberately not covered. The rule stays
unscoped and within its 2 KB budget: it has 25 bytes of headroom and the exception, written as one
line (about 117 bytes), is paid for by merging redundant bullets in the approval section (for
example "Confirmation covers one commit" and "If the user asks for changes"). Only the
explicit-approval requirement is MODIFIED; the budget requirement is unchanged. If the exception
cannot fit without hurting clarity, raise the budget then, as a deliberate follow-up.
*Alternative:* leave the rule alone and put the override only in the command (rejected: the rule
would win); an opt-in `--auto` flag (rejected by the user, who wants the run unattended by default);
raising the budget to 2.5 KB (rejected for now: it taxes every session).

**3. Hard guards are opt-in settings, soft guards are in the command.** "Never push" in a command
is an instruction, not enforcement. The README ships a `permissions.deny` snippet for `git push*`
and an `allow` snippet (`git add`, `git commit`, test/build commands, `openspec`) so a run does not
stall on prompts. The installer must never touch `settings.json` (existing requirement), so these
are copy-paste snippets. The command also restates its limits in its own body because the rule is
the only other place they live.

**4. `jois:apply` is `opsx:apply` plus a commit step, and shares its change-selection logic.**
`toolkit/commands/opsx/apply.md` is generated and reflects the installed `openspec` version, so the
jois copy is a standalone file that restates the steps (select change, `openspec status`,
`openspec instructions apply`, read context files, implement, tick tasks). It replaces the pause
block with: run checks, split by concern, stage by path, commit, continue. A comment in the file
names its origin so a maintainer can re-sync when `opsx:apply` changes. *Alternative:* instruct
the command to read and follow `opsx:apply` at runtime (rejected: loads a second large command and
depends on its exact wording).

**5. Branch handling.** If the current branch is the default branch (`main` or `master`, or what
`git symbolic-ref refs/remotes/origin/HEAD` names), the command creates `jois/<change-name>`
before the first commit and reports it. On any other branch it commits in place. No other git state
is changed: no reset, rebase, amend or stash.

**6. Checks before each commit.** The command runs the commands `CLAUDE.md` or the project's
config name for tests and build. If none can be found it says so and stops before the first
commit instead of committing unchecked. A failing check stops the run unless the next step is the
fix for that very failure.

**7. `jois:stage` follows `opsx:apply`'s pause exactly, in a loop.** Per turn: read status,
choose a concern, stage by path, print summary, message and a fresh word, end the turn, no tool
call after. The typed word triggers the commit and the next concern in the same turn. The loop
ends at a clean tree. State lives in the conversation (the last word, the commits made), not in
files.

**8. `jois:stage` edge cases.**
- *Unsafe untracked or modified files* (`.env`, `*.pem`, key files, `node_modules`, build output
  that is not gitignored): never staged, named as skipped, and excluded from the "clean tree"
  test. Recommended by the user's brief; stricter than asking each time.
- *A file with two concerns*: apply a prepared patch to the index with `git apply --cached`
  (interactive `git add -p` does not work here). When a clean patch cannot be built, report the
  file and ask the user to split the edit.
- *Pre-staged changes*: treated as part of the tree and analysed with the rest; the command says
  so and unstages and restages by concern when they mix concerns.

**9. Commands are hidden with `disable-model-invocation: true`.** This is the standard frontmatter
for a user-only command or skill. Claude Code lists a skill's description only when the model may
invoke it, so the flag removes the entry while `/name` still works. The first task verifies this
on 2.1.299 with a throwaway command and `/context`, as `review-tracking` verified its own
assumptions; if the flag does not shrink the listing, this decision and the matching
requirement are revised before anything else ships. `coding-standards` stays unflagged.

**10. `openspec update` does not touch the installed commands; it writes project folders.** Verified
in task 2.3 (openspec 1.13.0, `delivery: both`, scratch project, installed files backed up): `openspec
update` writes `<project>/.claude/commands/opsx/*.md` and `<project>/.claude/skills/openspec-*/`, and
`~/.claude/commands/opsx` stays byte-identical. The flag therefore survives in the global install and
in `toolkit/commands/opsx/`. In a project where `openspec update` runs, the generated project
commands carry no flag and are listed in that project's sessions (and the generated project skills
are model-discoverable); that is outside this toolkit and not fixed here. The README says so and
suggests either removing the project `.claude/commands/opsx` (the global one serves) or re-adding the
flag. The docs check guards only `toolkit/commands/`. An installer step that patches the flag in is
rejected: it would make installed files differ from the source and break the `differs` comparison.

**11. Versioning and the docs check.** `toolkit/commands/jois/*.md` carry `metadata.version` and
`last_updated`. To avoid editing the same glob `review-tracking` extends, `_versioned_items` gains
`commands/jois/*.md` as its own line; whichever change lands second merges one added line. A new
check requires `disable-model-invocation: true` on every file under `toolkit/commands/`. The
unscoped rule budget is unchanged.

## Risks / Trade-offs

- [The unattended run commits something wrong] -> bounded by green checks, one-concern commits,
  current-branch-only and local-only; the closing report lists every hash so the user can review,
  squash or `git reset` themselves. The cost is accepted by the user.
- [Soft "never push"] -> the README `permissions.deny` snippet is the hard block; without it only
  the rule and command text prevent a push.
- [The rule exception is ambiguous to the model] -> it names the trigger (`/jois:apply` started
  by the user) and the limits; tested in the tasks by running a small change end to end.
- [`disable-model-invocation` does not remove the listing, or also blocks `/name`] -> verified
  first; the work stops there if it does.
- [`openspec update` regenerates unflagged project copies] -> it never touches the global install;
  the README documents removing or re-flagging the project `.claude/commands/opsx`.
- [Tightening the rule's wording loses meaning] -> the existing rule tests and a review of the
  merged bullets in the task; the budget is the fallback.
- [Both this change and `review-tracking` edit `api/check_docs.py` and `toolkit/README.md`]
  -> edits are additive and in separate hunks; whichever lands second resolves a trivial merge.

## Migration Plan

Land in task order. After merging, refresh the global install with `Install-Toolkit.ps1 -Force`
so `~/.claude/rules/commit-hygiene.md` (which has slightly different wording from the toolkit
copy) and `~/.claude/commands` are replaced, then start a new session and check `/context`.
Rollback: revert the commits and reinstall.

## Open Questions

- Does the flag behave the same for a namespaced command in `~/.claude/commands/<ns>/`? (Covered
  by task 1.1.)
- Should `jois:apply` later gain an optional agent variant? Not decided; out of scope here.
