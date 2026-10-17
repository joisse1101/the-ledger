## ADDED Requirements

### Requirement: Manual-only PR skill
The toolkit SHALL include a skill `write-pr` that opens GitHub pull requests for the commits on the
current branch. It SHALL declare `disable-model-invocation: true`, so it runs only when the user
invokes it by name and is not listed in the session context. The folder SHALL carry the PR template
and guidelines as support files and SHALL be complete when copied by hand.

#### Scenario: Not offered unprompted
- **WHEN** a session starts with the skill installed
- **THEN** the skill's description SHALL NOT be loaded into the session context and Claude SHALL NOT start it on its own

#### Scenario: Refuses the default branch
- **WHEN** the skill is invoked while on `main`
- **THEN** it SHALL open no PR and SHALL tell the user to switch to a feature branch

### Requirement: PRs grouped by concern and confirmed
The skill SHALL read the commits on the branch since the base branch, propose groups of commits
that each form one logical unit of work, and wait for the user to confirm the grouping before
creating anything. Refactoring and feature commits SHALL NOT share a group. Test, docs and OpenSpec
archive commits SHALL join the group they belong to and SHALL form their own group only when the
whole branch is that kind of change. A group over about 400 changed lines SHALL be flagged.

#### Scenario: Small branch
- **WHEN** all commits on the branch form one concern
- **THEN** the skill SHALL propose a single PR

#### Scenario: Mixed branch
- **WHEN** the branch holds a refactor and an unrelated feature
- **THEN** the skill SHALL propose separate PRs for them and SHALL NOT create any until the user confirms

#### Scenario: Dependent groups
- **WHEN** a later group depends on an earlier one
- **THEN** its PR SHALL be based on the earlier group's branch and the skill SHALL tell the user to rebase it after the earlier PR merges

### Requirement: PR content follows the template
Each PR SHALL have a conventional-commit title (`type(scope): subject`) that is the commit subject
for a single-commit group and a new title otherwise. The body SHALL follow the template: a summary
that explains why, the type of change ticked from the commit types (breaking when a commit is
marked `!` or `BREAKING CHANGE`), the commit titles under changes made, and a testing section. The
Related Issues section SHALL be omitted when there are no related issues. The body SHALL have no
visual-proof section and SHALL end with the attribution line the environment requires.

#### Scenario: Testing section
- **WHEN** a group adds or changes test files
- **THEN** the body SHALL list those tests and tick the automated-tests box

#### Scenario: Manual test results from OpenSpec
- **WHEN** the branch has an OpenSpec change whose `tasks.md` records manual test steps or results
- **THEN** the body SHALL include them and tick the manual-testing box

#### Scenario: No recorded manual testing
- **WHEN** no manual test steps are recorded
- **THEN** the manual-testing box SHALL stay unticked

### Requirement: Diff self-review before opening
Before proposing a PR the skill SHALL scan the group's diff. It SHALL block, naming the file, when
the diff contains a secret, credential, `.env` file or build artifact. It SHALL warn, and not block,
on debug prints and commented-out code.

#### Scenario: Secret in the diff
- **WHEN** a group's diff adds a `.env` file or an API key
- **THEN** the skill SHALL NOT create that PR and SHALL name the file

#### Scenario: Debug print in the diff
- **WHEN** a group's diff adds a `console.log` or `print` call
- **THEN** the skill SHALL warn and SHALL still allow the PR

### Requirement: Confirmation before publishing
The skill SHALL show each PR's title, body, base and head and name a confirmation word before it
pushes or runs `gh pr create`. It SHALL proceed only when the user types that word. It SHALL use a
plain `git push` and SHALL NOT force-push. If an open PR already exists for the branch, it SHALL
report it and open nothing.

#### Scenario: Word not typed
- **WHEN** the user replies with anything other than the confirmation word
- **THEN** nothing SHALL be pushed and no PR created

#### Scenario: PR already open
- **WHEN** an open PR already exists for the branch
- **THEN** the skill SHALL report it and SHALL NOT push or create another

### Requirement: The skill never merges
The skill SHALL NOT merge a PR, enable auto-merge, or pass `--auto`. A hook declared by the skill
SHALL block `gh pr merge` and the merge API endpoint while the skill runs.

#### Scenario: Merge attempted during the skill
- **WHEN** a merge command is attempted while the skill is running
- **THEN** the hook SHALL block it and the PR SHALL stay open

### Requirement: Merge-order summary
When it finishes, the skill SHALL list every PR it opened with number, title, URL and base, in the
order the user should merge them, with the `gh pr merge <number> -s -d` command for each. Dependent
PRs SHALL come in stack order; independent PRs SHALL be marked as any order. It SHALL run none of
these commands.

#### Scenario: Stacked PRs
- **WHEN** the skill opened PR 31 and PR 32 where 32 is based on 31's branch
- **THEN** the summary SHALL list 31 before 32 and say 32 needs a rebase after 31 merges

#### Scenario: No PR opened
- **WHEN** the skill stopped before creating any PR
- **THEN** the summary SHALL say that none were opened and why
