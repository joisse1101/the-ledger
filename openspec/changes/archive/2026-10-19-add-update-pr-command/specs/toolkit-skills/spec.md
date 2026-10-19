## ADDED Requirements

### Requirement: Manual-only PR update command
The toolkit SHALL include a command `jois:update-pr`, the single file
`toolkit/commands/jois/update-pr.md`, that updates the open PR of the current branch. It SHALL declare
`disable-model-invocation: true`, SHALL carry the PR body template, the ticking rules and the
verification rules inside it, and SHALL be complete when copied by hand. It SHALL find the PR with the
current branch as head. If no open PR exists it SHALL change nothing and SHALL tell the user to use
`/jois:write-pr`. It SHALL NOT merge a PR, enable auto-merge or pass `--auto`, and a hook in its
frontmatter SHALL block `gh pr merge` and the merge API endpoint from the moment it is invoked.

#### Scenario: Not offered unprompted
- **WHEN** a session starts with the command installed
- **THEN** its description SHALL NOT be loaded into the session context and Claude SHALL NOT start it on its own

#### Scenario: No open PR
- **WHEN** the command is invoked on a branch with no open PR
- **THEN** it SHALL push nothing, edit nothing and tell the user to use `/jois:write-pr`

#### Scenario: Merge attempted
- **WHEN** a merge command is attempted in a session where `/jois:update-pr` has been invoked
- **THEN** the hook SHALL block it and the PR SHALL stay open

### Requirement: Update is confirmed before anything is published
The update command SHALL present everything it will do, namely any restack, any push, and the new title
and body with a diff against the live body, and name a confirmation word before it rebases, pushes or
edits the PR. It SHALL proceed only when the user types that word. It SHALL use a plain `git push`,
except that a restack the user confirmed SHALL push with `--force-with-lease`; it SHALL NOT use `--force`.
It SHALL NOT rename the branch. It SHALL pass the body to `gh pr edit` from a file outside the
repository, never inline in the shell command text.

#### Scenario: Word not typed
- **WHEN** the user replies with anything other than the confirmation word
- **THEN** nothing SHALL be rebased, pushed or edited

#### Scenario: Body diff shown
- **WHEN** the command has a regenerated body
- **THEN** the presentation SHALL show the difference between the live body and the new body, not only the new body

#### Scenario: Body quotes the hook message
- **WHEN** the new body contains the words of the hook's own message, including `gh pr merge`
- **THEN** the PR SHALL be edited and the hook SHALL NOT block it

#### Scenario: Plain push
- **WHEN** the branch has commits the remote head lacks and no restack is needed
- **THEN** the command SHALL push with a plain `git push`

### Requirement: Restack after the base PR merged
When the PR's base is a branch other than the default branch, the PR under it has merged and the base
branch still exists, the update command SHALL offer to restack: rebase the branch onto the remote
default branch from the old base with `git rebase --onto`, push with `--force-with-lease`, and retarget
the PR to the default branch with `gh pr edit --base`. It SHALL NOT delete the old base branch. On a
rebase conflict it SHALL abort the rebase, leave the branch as it was and report the conflict. If GitHub
already closed the PR because its base branch was deleted, it SHALL say that the PR cannot be
reopened and tell the user to use `/jois:write-pr`.

#### Scenario: Stacked PR after its base merged
- **WHEN** PR 32 is based on `feat/a`, PR 31 from `feat/a` has merged and `feat/a` still exists
- **THEN** the command SHALL propose rebasing `feat/b` onto `origin/main` from `feat/a`, a `--force-with-lease` push and retargeting PR 32 to `main`

#### Scenario: Base still open
- **WHEN** the PR's base branch has an open PR
- **THEN** the command SHALL NOT restack

#### Scenario: Rebase conflict
- **WHEN** the rebase stops on a conflict
- **THEN** the command SHALL abort the rebase, leave the branch unchanged and report the conflict

#### Scenario: Base branch deleted
- **WHEN** the PR is closed because its base branch was deleted
- **THEN** the command SHALL change nothing and tell the user to use `/jois:write-pr`

### Requirement: PR body is refreshed from the branch
The update command SHALL regenerate the body from the same template, ticking rules and verification
rules as `jois:write-pr`, from the commits the PR now holds, and SHALL keep the title unless the user
asks to change it or it no longer fits the commits. A verification bullet SHALL state no result its
source lacks. It SHALL tell the user when the live body has content that the new body drops.

#### Scenario: Commit added after the PR was opened
- **WHEN** the branch gained a commit after the PR was opened
- **THEN** the new body's Changes Made SHALL list that commit and the presentation SHALL show it in the diff

#### Scenario: Title kept
- **WHEN** the user did not ask for a new title and the existing title still fits the commits
- **THEN** the command SHALL NOT change the title

#### Scenario: Hand-written content in the live body
- **WHEN** the live body holds text that the template does not produce
- **THEN** the presentation SHALL name that text as dropped and the command SHALL keep it only if the user says so

### Requirement: Shared PR sections stay identical
The docs check SHALL fail and name both files when the "PR body template" or "Author Verification"
section of `toolkit/commands/jois/update-pr.md` differs from the same section of
`toolkit/commands/jois/write-pr.md`.

#### Scenario: Sections differ
- **WHEN** the "PR body template" section of `update-pr.md` differs from that of `write-pr.md`
- **THEN** the docs check SHALL fail and name both files

#### Scenario: Sections match
- **WHEN** both sections are identical in the two files
- **THEN** the docs check SHALL NOT report them
