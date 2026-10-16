## Why

Finishing an OpenSpec change today means answering a confirmation word after every concern, which
turns a watch-it-run task into babysitting. There is also no tool for the other common case: a
working tree that has piled up mixed edits and needs to be committed in clean, single-concern
steps. Separately, every installed slash command is listed in each new session's skill listing,
spending context on commands that only the user ever starts.

## What Changes

- New `jois` command namespace in `toolkit/commands/jois/`, installed as `/jois:apply` and
  `/jois:stage`.
- `/jois:apply`: `opsx:apply` on the main thread with the commit pause removed. After each
  completed concern it runs tests and build and, when green, stages by explicit path and commits
  without a confirmation word. Current branch only (a branch is created first when started on
  `main`), never pushes, amends or forces. It still stops on an ambiguous task, scope beyond the
  spec, a design flaw, red tests or build, a blocker or an interruption, and ends with a list of
  the commits it made.
- `/jois:stage`: clears a messy working tree, independent of any OpenSpec change. It picks one
  concern at a time per the commit-hygiene rule, stages it by explicit path, prints the summary and
  proposed message, names a fresh confirmation word and ends the turn. The typed word commits that
  concern and the command moves on to the next, until `git status` is clean.
- `commit-hygiene` rule gains one exception: running `/jois:apply` authorizes commits for that run
  only (current branch, no push, no amend). Everywhere else, including `/jois:stage`, the
  confirmation word still applies. The rule stays within its existing 2 KB budget: the exception is
  one short line, paid for by tightening existing wording.
- Every command under `toolkit/commands/` (the new ones and the existing `opsx:*` set) declares
  `disable-model-invocation: true`, so its description is no longer loaded into a new session; the
  user can still type it. `coding-standards` is left model-discoverable on purpose.
- `toolkit/README.md` documents the namespace, context hiding, and opt-in `settings.json`
  snippets: a `permissions.deny` for `git push*` as a hard guard for `/jois:apply`, and an `allow`
  list so an unattended run does not stall on prompts. The installer never edits `settings.json`.
- `api/check_docs.py` validates the new command frontmatter and the new rule budget.

## Capabilities

### New Capabilities
- `jois-apply`: the unattended apply command, its commit limits, its stop conditions and its
  closing report.
- `jois-stage`: the clear-the-working-tree command and its one-concern-at-a-time confirmation loop.

### Modified Capabilities
- `toolkit-coding-standards`: `commit-hygiene` is allowed a `/jois:apply` exception.
- `toolkit-skills`: commands are hidden from the session listing, and the `jois` namespace's
  commands carry a version that the docs check validates.

## Impact

- New: `toolkit/commands/jois/apply.md`, `toolkit/commands/jois/stage.md`.
- Edited: `toolkit/commands/opsx/*.md` (frontmatter flag), `toolkit/rules/commit-hygiene.md`,
  `toolkit/README.md`, `api/check_docs.py` and `api/tests/test_check_docs.py`; `wiki/` pages and
  `CLAUDE.md` only if documented behavior changes (the wiki has no toolkit page today; confirm in
  the docs task).
- Refresh of the user's global install (`~/.claude/commands`, `~/.claude/rules`) via
  `Install-Toolkit.ps1 -Force`.
- Note: `openspec update` writes unflagged `opsx:*` copies into a project's `.claude/` and leaves the
  global install alone; the README says how to handle that. See design.
- Independent of the in-progress `review-tracking` change, which this change does not read, edit
  or depend on. `jois:review` is out of scope.
- Not affected: the dashboard (`api/`, `web/`, `widget/`, `gateway/`), and the skill listings the
  toolkit does not own (claude.ai sync, built-in and project skills).
