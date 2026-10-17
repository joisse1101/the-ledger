## Context

See proposal.md - Why. The toolkit already has one skill (`coding-standards`) and a command with a
confirmation-word loop (`jois/stage.md`) to copy the pattern from. Commands in this repo set
`disable-model-invocation: true`; the new skill sets the same flag in its own frontmatter. The
`gh` CLI is available and used for all GitHub calls. History shows PRs squash-merged with
`gh pr merge -s -d`, so the PR title becomes the commit on `main`.

## Goals / Non-Goals

**Goals**
- One run turns a branch into one or more reviewable PRs without the user retyping the template.
- Nothing is published or merged without the user.

**Non-Goals**
- Running tests or CI checks (CI runs on every PR).
- Editing or updating an existing PR.
- Posting screenshots or other visual proof.
- A user-level deny rule for `gh pr merge` (separate settings change).

## Decisions

**Folder layout.** `toolkit/skills/write-pr/SKILL.md` holds the workflow and the never-merge rule
only. `pr-template.md` and `guidelines.md` sit beside it, read on demand. The merge guard is an
inline `PreToolUse` command in the frontmatter, not a script file: a hook command cannot reliably
locate a script inside an installed skill folder (tested on 2.1.302). This keeps the loaded text
small and the folder self-contained.
*Alternative:* everything in SKILL.md - rejected, the guidelines are long and only needed while writing a body.

**Grouping.** The skill proposes groups from commit types, scopes and touched paths, then waits for
confirmation. Tests, docs and archive commits attach to the group they describe, matching the
commit-hygiene rule. *Alternative:* strictly one PR per commit - rejected, it needs stacked branches
for every commit and a rebase after each squash-merge.

**Branches for later groups.** The first group uses the current branch only if it holds nothing
else; every other group gets a new `type/short-description` branch cherry-picked from the base.
A group that depends on an earlier one is based on that group's branch, so its PR shows only its own
commits, and the summary warns that it needs `git rebase --onto main` after the earlier PR squash-merges.
*Alternative:* split only when independent and otherwise open one PR - rejected by the user in favour of stacking.

**Title.** A single-commit group reuses the commit subject. A multi-commit group gets a new
`type(scope): subject`, lowercase and imperative, as in commit-hygiene, because the squash commit
takes it.

**Testing section.** No checks are run. Test files added or changed in the group are listed and the
automated box is ticked on the user's assumption that they were run. Manual steps and results come
from `tasks.md` of the OpenSpec change, found in `openspec/changes/<name>/` or the dated archive
folder whose commits are on the branch. No match means the manual box stays unticked.

**Self-review.** A scan of the added lines of the diff: secrets, `.env` files and build output block;
debug prints and commented-out code warn. *Alternative:* warn on everything - rejected, a leaked key
is not reversible once pushed.

**Never merging.** Three layers: the SKILL.md instruction, an `allowed-tools` list without merge,
and a skill-scoped `PreToolUse` hook on `Bash` that exits with a block when the command matches
`gh pr merge` or a merge call through `gh api`. `allowed-tools` only pre-approves, so it is not
counted as a guard.

**Confirmation.** Same word protocol as commit-hygiene: a common word that differs from the previous
prompt's, typed by the user, one word per PR batch shown. Push is `git push -u`, never forced.

**Summary.** Collected as each `gh pr create` returns its URL, then printed once at the end in merge
order: stack order first, independent PRs marked any order.

## Risks / Trade-offs

- [The frontmatter hook outlives the skill's steps] → verified on 2.1.302 that it stays active for the
  rest of the session once the skill is invoked; accepted, since the user merges in their own terminal.
- [Hook pattern misses an unusual merge spelling, such as an alias or `gh api` variant] → match on
  `pr merge` and `/merge` in the command text, and keep the instruction layer as well.
- [Stacked PRs need a rebase after each squash-merge] → the summary names the exact `git rebase --onto`
  step for each dependent PR.
- [Grouping heuristic proposes the wrong split] → the user confirms before anything is created.
- [Assumed-run tests] → the box reflects the user's stated assumption, and CI is the real check.
