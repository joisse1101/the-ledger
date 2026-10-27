## Context

`toolkit/commands/jois/write-pr.md` is one file of steps, guidelines, a body template and
verification rules. Step 1 stops on the base branch. Step 2 already reads `origin/<base>..HEAD`, and
step 8 already cuts every extra group's branch from `origin/<base>` and cherry-picks, so most of the
machinery exists. `allowed-tools` already holds `git branch:*` and `git switch:*`. Branch names are
specified only as `type/short-description` (step 3 and Best practices).

## Goals / Non-Goals

**Goals:**
- Run from the default branch with local commits ahead of `origin/<base>`, and leave local `<base>`
  equal to `origin/<base>` afterwards without losing any commit or uncommitted change.
- One written branch-name convention that step 3 and the spec both use.

**Non-Goals:**
- The `update-pr` command (a later change). It will reuse the branch-name rules.
- Renaming existing branches, enforcing names with hooks or CI.
- Any change to the merge-blocking hook.

## Decisions

**Reset with `git branch -f`, not `git reset --hard`.** `branch -f <base> origin/<base>` moves the ref
only, so the working tree and index are untouched and uncommitted changes survive. It refuses while
`<base>` is checked out, which forces the command to leave the default branch first. That is the
behavior wanted anyway. Alternative: `git switch <base>` plus `reset --hard`, rejected because it
discards the working tree.

**Reset last, gated on success.** The reset runs after the last push and `gh pr create` succeeded
and only when every commit listed in step 2 belongs to a group whose PR was created. A failure
anywhere leaves `<base>` as it was, so the commits are still on it and nothing needs recovery.
Cherry-picked commits have new hashes, so "covered" is decided by group membership, not by hash.

**Branching from the default branch.**
- One group, and `origin/<base>` is an ancestor of local `<base>`: `git switch -c <branch>`. The
  commits and any uncommitted changes come along. No cherry-pick.
- Several groups, or local `<base>` has diverged from `origin/<base>` (not a descendant): the
  existing path, `git switch -c <branch> origin/<base>` then cherry-pick, per group. Diverged local
  commits would otherwise drag already-merged hashes into the PR branch.
- The command stays on `<base>` until all PRs are opened, then switches to the last PR branch
  opened (the tip of a stack, or any independent one) so `branch -f` can run. "Return to the
  original branch" in step 8 applies only when the original was not the default branch.

**Confirmation word covers the reset.** Step 7 adds a line "after the PRs are pushed, local
`<base>` is set to `origin/<base>`" and the final summary reports it, so the user types the word
knowing it. A reset the presentation did not announce is not allowed.

**Branch names live in one subsection** under Guidelines ("Branch names"), replacing the Best
practices bullet and the clause in step 3. Rules: `<type>/<ticket>-<slug>` or `<type>/<slug>`; type is
a commit type; ticket only from a commit message or the current branch name (the same source rule as
Related Issues); ticket keeps tracker case, `#123` becomes `123`; slug lowercase kebab-case, 2 to 4
words, imperative, never a bare `fix`, `update` or `test`. Before use, check `git branch --list` and
`git ls-remote --heads origin <name>`; on a hit, propose another name. The type comes from the group
title's type, so the branch, title and commits agree. Short types win over `feature/` and `bugfix/`
because commits and PR titles already use them. `hotfix/` is dropped: there is no commit type or
production flow for it. Ticket case is the one uppercase exception, since it is an identifier.
`git ls-remote` needs adding to `allowed-tools`.

## Risks / Trade-offs

- A moved `<base>` loses its pointer to the old tip. Mitigated: the commits are on the pushed
  branches and the old tip stays in the reflog. The summary prints the old tip hash.
- A cherry-pick conflict on a dirty working tree can stop the run midway. The existing rule applies:
  `git cherry-pick --abort`, retry on the dependent group's branch. `<base>` is not reset because the
  gate has not been met.
- Ticket case versus the lowercase rule can look inconsistent; the exception is written next to the rule.
