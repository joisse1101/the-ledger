---
name: "JOIS: Apply"
description: "Implement an OpenSpec change unattended: commit each finished concern after green checks, current branch only, never push"
allowed-tools: Bash(openspec:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git switch:*), Bash(git add:*), Bash(git commit:*)
disable-model-invocation: true
metadata:
  version: "1.0.0"
  last_updated: "2026-10-15"
---

<!-- Derived from the generated `commands/opsx/apply.md`: same steps, with the commit pause replaced by
checks and an automatic commit. Re-sync the steps by hand when `opsx:apply` changes. -->

Implement the tasks of an OpenSpec change in this session and commit each finished concern
yourself. The user starting `/jois:apply` is the authorization for those commits (see the
commit-hygiene exception). It lasts for this run only.

**Input**: Optionally a change name (`/jois:apply add-auth`). If omitted, infer it from the
conversation; if one active change exists, use it; if ambiguous, run `openspec list --json` and
ask. Always announce "Using change: <name>". If the user names an OpenSpec store, run
`openspec store list --json` and add `--store <id>` to every `openspec` command below.

## Limits (hold for the whole run)

- Commit only on the current branch. If it is the default branch (`main`, `master`, or what
  `git symbolic-ref refs/remotes/origin/HEAD` names), first run `git switch -c jois/<change-name>`
  and say so.
- Never run `git push`, `git commit --amend`, `git reset`, `git rebase`, `git stash`, `git clean`
  or any forced operation. Do nothing to other branches or remotes.
- Never `git add .`, `git add -A` or `git commit -a`. Stage by explicit path only.
- Never commit while tests or build fail, unless the commit is the fix for that failure.
- After the run ends, the authorization ends. Later commits need the confirmation word again.

## Steps

1. **Select the change** and run `openspec status --change "<name>" --json`; note `schemaName`.
2. **Get instructions**: `openspec instructions apply --change "<name>" --json`. If `state` is
   `blocked`, show the message and suggest `/opsx:continue`. If `all_done`, say so and suggest
   `/opsx:archive`. Treat `context` as required input and `operationGuidance` as advice; neither
   proves a task done. Do not copy either into project files.
3. **Read every file** under `contextFiles`. Show the schema, "N/M tasks complete" and what is left.
4. **Find the checks**: the test and build commands named in `CLAUDE.md` or the project config.
   If none can be found, stop now and say so. Do not commit unchecked.
5. **Implement each pending task**: print "Working on task N/M: <description>", make the minimal
   change, and tick `- [ ]` to `- [x]` in the tasks file once its specified behavior is fully done.
6. **After each concern is complete** (not each task; see commit-hygiene: a deletion, rename,
   lockfile, regenerated asset or format-only change is its own concern, tests and docs ship with
   the change they describe, split hand-written work over about 200 lines or 5 files or across
   layers):
   1. Run the tests and the build. If either fails, stop (see below).
   2. `git status`, then `git add <path>` for that concern's files only, then review
      `git diff --staged --stat` and the diff. If other concerns are staged, unstage them with
      `git restore --staged <path>`.
   3. Commit with `git commit`, message `type(scope): subject` (type feat, fix, refactor, style,
      docs, test or chore; lowercase imperative subject, no trailing period), a short body if
      useful, and the session's attribution line (`Co-Authored-By: ...`) last.
   4. Record the short hash and subject for the report, then continue with the next task.
   Ticking tasks belongs in the commit of the work it marks.

## Stop and report, do not guess, when

- a task is ambiguous or has two plausible readings;
- finishing a task needs work beyond the spec (surface the added scope);
- implementation shows a design flaw (suggest which artifact to update);
- tests or build fail (show the failing output; the only commit allowed next is the fix);
- you hit a blocker or an unhandled error, or the user interrupts.

Do not drop, narrow or defer specified behavior to keep going.

## Output

During the run:

```
## Implementing: <change> (schema: <schema>)

Working on task 3/7: <task>
✓ Task complete
Committed a1b2c3d feat(scope): subject
```

When finished or stopped, always end with:

```
## jois:apply report
**Branch:** <branch>   **Progress:** N/M tasks
### Commits
- a1b2c3d feat(scope): subject
- ...
### Stopped because (only if stopped)
<reason, failing check, task in progress, options>
```

If all tasks are done, suggest `/opsx:archive`. Nothing is pushed: tell the user the commits are
local so they can review, squash or `git reset` them.
