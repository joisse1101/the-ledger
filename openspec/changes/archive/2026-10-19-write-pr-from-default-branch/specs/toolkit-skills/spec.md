## MODIFIED Requirements

### Requirement: Manual-only PR skill
The toolkit SHALL include a command `jois:write-pr`, the single file
`toolkit/commands/jois/write-pr.md`, that opens GitHub pull requests for the commits on the current
branch. It SHALL declare `disable-model-invocation: true`, so it runs only when the user invokes it by
name and is not listed in the session context. The file SHALL carry the PR guidelines, the PR template
and the verification rules inside it and SHALL be complete when copied by hand. The toolkit SHALL NOT
also ship a `write-pr` skill. The command SHALL NOT use the default branch as the head of a PR. The
requirements below that say "the skill" apply to this command.

#### Scenario: Not offered unprompted
- **WHEN** a session starts with the command installed
- **THEN** its description SHALL NOT be loaded into the session context and Claude SHALL NOT start it on its own

#### Scenario: Refuses the default branch
- **WHEN** the command is invoked while on `main` and `main` has no commits beyond `origin/main`
- **THEN** it SHALL open no PR and SHALL say that there are no commits to open a PR for

#### Scenario: Default branch is never a PR head
- **WHEN** the command opens PRs from commits made on `main`
- **THEN** every PR head SHALL be a new branch and none SHALL be `main`

#### Scenario: Single entry point
- **WHEN** the toolkit is installed
- **THEN** `/jois:write-pr` SHALL exist and no `write-pr` skill SHALL be copied from the toolkit

### Requirement: Confirmation before publishing
The skill SHALL show each PR's title, body, base and head and name a confirmation word before it
pushes or runs `gh pr create`. When it will reset the default branch, it SHALL list that reset in the
same presentation, so that the word authorizes it. It SHALL proceed only when the user types that
word. It SHALL use a plain `git push` and SHALL NOT force-push. If an open PR already exists for the
branch, it SHALL report it and open nothing.

#### Scenario: Word not typed
- **WHEN** the user replies with anything other than the confirmation word
- **THEN** nothing SHALL be pushed, no PR created and the default branch left as it was

#### Scenario: PR already open
- **WHEN** an open PR already exists for the branch
- **THEN** the skill SHALL report it and SHALL NOT push or create another

#### Scenario: Reset is announced
- **WHEN** the command was invoked on `main` with commits ahead of `origin/main`
- **THEN** the presentation SHALL state that local `main` will be set to `origin/main` after the PRs are pushed

## ADDED Requirements

### Requirement: Default branch is reset after publishing
When invoked on the default branch with commits ahead of the remote default branch, the skill SHALL
create each PR branch from those commits, publish the PRs, and only then set the local default branch
to the remote default branch with `git branch -f`. It SHALL NOT use `git reset --hard`, so uncommitted
changes survive. It SHALL NOT reset the default branch unless every commit ahead of the remote is on a
branch that has been pushed, and it SHALL NOT reset it if any push or PR creation failed. It SHALL
finish on a branch other than the default branch.

#### Scenario: One group from main
- **WHEN** all commits ahead of `origin/main` form one group and the user types the confirmation word
- **THEN** the skill SHALL create the branch from `main`, push it, open the PR, set local `main` to `origin/main` and finish on the new branch

#### Scenario: Several groups from main
- **WHEN** the commits ahead of `origin/main` form two groups
- **THEN** the skill SHALL branch each group from `origin/main`, push both, open both PRs, set local `main` to `origin/main` and finish on one of the new branches

#### Scenario: Push fails
- **WHEN** a push or `gh pr create` fails on one of the branches
- **THEN** local `main` SHALL keep its commits and the skill SHALL report the failure

#### Scenario: Uncommitted changes
- **WHEN** the working tree has uncommitted changes when `main` is reset
- **THEN** those changes SHALL remain in the working tree

### Requirement: Branch names follow a convention
A branch the skill creates SHALL be named `<type>/<ticket>-<slug>` when a commit message in the group
or the current branch name references a ticket, and `<type>/<slug>` otherwise. The skill SHALL NOT
invent a ticket. The type SHALL be a commit type: `feat`, `fix`, `refactor`, `style`, `docs`, `test` or
`chore`. The slug SHALL be lowercase kebab-case made of letters, digits and hyphens, two to four words,
imperative, and SHALL NOT be a bare `fix`, `update` or `test`. A ticket id SHALL keep the case the
tracker writes it, and a GitHub issue `#123` SHALL appear as `123`. If the name already exists
locally or on `origin`, the skill SHALL propose another name and SHALL NOT reuse or overwrite it. It
SHALL NOT rename the current branch.

#### Scenario: No ticket
- **WHEN** a feature group has no ticket reference
- **THEN** the branch SHALL be named like `feat/add-oauth-login`

#### Scenario: Jira ticket
- **WHEN** a commit message in a fix group says `Fixes PROJ-456`
- **THEN** the branch SHALL be named like `fix/PROJ-456-prevent-negative-quantity`

#### Scenario: GitHub issue
- **WHEN** a commit message in a fix group says `Closes #123`
- **THEN** the branch SHALL be named like `fix/123-prevent-negative-quantity`

#### Scenario: Type matches the commit type
- **WHEN** a group's commits are `refactor` commits
- **THEN** the branch SHALL start with `refactor/` and SHALL NOT start with `feature/` or `bugfix/`

#### Scenario: Name already taken
- **WHEN** `feat/add-oauth-login` already exists locally or on `origin`
- **THEN** the skill SHALL propose a different name and SHALL NOT push to the existing one

#### Scenario: Current branch kept
- **WHEN** the command is invoked on a feature branch with one group
- **THEN** the PR head SHALL be the current branch under its existing name
