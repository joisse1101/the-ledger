## MODIFIED Requirements

### Requirement: PRs grouped by concern and confirmed
The skill SHALL read the commits on the branch since the base branch as it is on the remote, not as
it is in the local checkout, propose groups of commits that each form one logical unit of work, and
wait for the user to confirm the grouping before creating anything. Refactoring and feature commits
SHALL NOT share a group. Test, docs and OpenSpec archive commits SHALL join the group they belong to
and SHALL form their own group only when the whole branch is that kind of change. A group over about
400 changed lines SHALL be flagged.

#### Scenario: Small branch
- **WHEN** all commits on the branch form one concern
- **THEN** the skill SHALL propose a single PR

#### Scenario: Mixed branch
- **WHEN** the branch holds a refactor and an unrelated feature
- **THEN** the skill SHALL propose separate PRs for them and SHALL NOT create any until the user confirms

#### Scenario: Dependent groups
- **WHEN** a later group depends on an earlier one
- **THEN** its PR SHALL be based on the earlier group's branch and the skill SHALL tell the user to rebase it after the earlier PR merges

#### Scenario: Local base branch is behind the remote
- **WHEN** the local base branch lacks commits that are already on the remote base and the current branch was cut from the remote base
- **THEN** the skill SHALL list only the commits the branch adds and SHALL NOT count the merged commits in any group or size

### Requirement: Merge-order summary
When it finishes, the skill SHALL list every PR it opened with number, title, URL and base, in the
order the user should merge them, with a `gh pr merge` command for each. Dependent PRs SHALL come in
stack order; independent PRs SHALL be marked as any order. A PR that no other opened PR is based on
SHALL be given `gh pr merge <number> -s -d`. A PR that another opened PR is based on SHALL be given
`gh pr merge <number> -s` without `-d`, because deleting its branch closes the PR based on it and
that PR can then be neither retargeted nor reopened. For each later PR in a stack the summary SHALL
then list, in order, rebasing it onto the base branch, pushing it with `--force-with-lease`,
retargeting it to the base branch, and deleting the earlier branch. It SHALL run none of these
commands.

#### Scenario: Stacked PRs
- **WHEN** the skill opened PR 31 and PR 32 where 32 is based on 31's branch
- **THEN** the summary SHALL list 31 before 32, give 31 a merge command without `-d`, and list the rebase, force-with-lease push, retarget and branch deletion for 32 after 31 merges

#### Scenario: Independent PRs
- **WHEN** the skill opened two PRs that are not based on each other
- **THEN** the summary SHALL mark them any order and give each `-s -d`

#### Scenario: Last PR in a stack
- **WHEN** the skill opened PR 31 and PR 32 where 32 is based on 31's branch
- **THEN** the merge command for 32 SHALL include `-d`

#### Scenario: No PR opened
- **WHEN** the skill stopped before creating any PR
- **THEN** the summary SHALL say that none were opened and why

## ADDED Requirements

### Requirement: PR body is passed from a file
The skill SHALL write each PR body, without the source tags, to a temporary file outside the repository
using the file-writing tool, and SHALL pass it to `gh pr create` with `--body-file <path>`. It SHALL NOT
put the body inline in the shell command text. The merge-blocking hook SHALL remain unchanged, so
shell command text that contains the merge words is still blocked.

#### Scenario: Body quotes the hook message
- **WHEN** a PR body contains the words of the hook's own message, including `gh pr merge`
- **THEN** the PR SHALL be created and the hook SHALL NOT block it

#### Scenario: Merge words in other command text
- **WHEN** any shell command contains `gh pr merge` in its text after the command has been invoked
- **THEN** the hook SHALL still block it

#### Scenario: Body file stays out of the repository
- **WHEN** the skill writes a body file
- **THEN** the file SHALL be outside the repository's working tree and SHALL NOT appear in `git status`
