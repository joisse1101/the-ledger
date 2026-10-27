## MODIFIED Requirements

### Requirement: PR content follows the template
Each PR SHALL have a conventional-commit title (`type(scope): subject`) that is the commit subject
for a single-commit group and a new title otherwise. The body SHALL follow the template: a summary
that explains why, the type of change ticked from the commit types (breaking when a commit is
marked `!` or `BREAKING CHANGE`), the commit titles under changes made, and a testing section. The
testing section SHALL hold the automated and manual checkboxes, an Author Verification subsection and
a How to Test This PR subsection. The Related Issues section SHALL be omitted when there are no
related issues. The body SHALL have no visual-proof section and SHALL end with the attribution line the
environment requires.

#### Scenario: Testing section
- **WHEN** a group adds or changes test files
- **THEN** the body SHALL list those tests and tick the automated-tests box

#### Scenario: Manual test results from OpenSpec
- **WHEN** the branch has an OpenSpec change whose `tasks.md` records verification tasks with observed results, and at least one is a manual check, meaning a command run or behavior observed by hand
- **THEN** Author Verification SHALL hold one bullet per check with the command or input and the recorded result, and the manual-testing box SHALL be ticked

#### Scenario: No recorded manual testing
- **WHEN** Author Verification holds no manual check
- **THEN** the manual-testing box SHALL stay unticked

#### Scenario: No hard-coded counts
- **WHEN** the body reports a test count or similar figure
- **THEN** that figure SHALL come from a recorded result and SHALL NOT be a value fixed in the template

## ADDED Requirements

### Requirement: Author verification is recorded, not invented
The skill SHALL draft Author Verification from the matching OpenSpec `tasks.md`. It SHALL NOT state an
observed result that no source records. A checked verification task with no recorded result SHALL
yield a bullet that names the check without a result, and the skill SHALL flag it. A task that is not
verification SHALL NOT yield a bullet. When `tasks.md` is missing, holds no verification task, or
holds a task with no recorded result, the skill SHALL ask the user once, covering every group, what
they ran and saw, before presenting any PR. It SHALL turn the user's answer into bullets and SHALL NOT
add results the user did not give. When the user has none, it SHALL write that none were recorded.

#### Scenario: Result recorded
- **WHEN** a verification task in `tasks.md` records an observed result
- **THEN** its bullet SHALL carry that result

#### Scenario: Checked task without a result
- **WHEN** a verification task is checked and records no result
- **THEN** its bullet SHALL name the check, SHALL NOT state an outcome, and SHALL be flagged

#### Scenario: Gaps across several groups
- **WHEN** two groups each lack recorded verification
- **THEN** the skill SHALL ask the user once for both and SHALL NOT ask per group

#### Scenario: No OpenSpec change
- **WHEN** the group's commits touch no OpenSpec change
- **THEN** the skill SHALL ask the user what verification they ran

#### Scenario: Nothing to report
- **WHEN** the user says they ran no verification
- **THEN** Author Verification SHALL state that none was recorded and the manual box SHALL stay unticked

### Requirement: Reviewer steps are grounded and sourced
The skill SHALL suggest How to Test This PR steps from the group's commits and diff, its `tasks.md`
and the repository's own documents. Each step SHALL be a checkout step, a run step or a read step. A
run step SHALL use a command that a document states and that the diff points to, and every path in
it SHALL exist in the checkout; a step failing that check SHALL be dropped. The skill SHALL NOT invent
a command or flag that no document mentions. The skill SHALL show each step and each verification
bullet with its source when it presents the PR, and SHALL NOT include those source tags in the PR body.

#### Scenario: Documented command the diff points to
- **WHEN** the diff changes files under a directory whose documented test command is known
- **THEN** a run step SHALL use that command

#### Scenario: Path missing from the checkout
- **WHEN** a candidate run step names a script or path that does not exist
- **THEN** the skill SHALL drop that step

#### Scenario: Undocumented command
- **WHEN** the diff adds a script and no document says how to run it
- **THEN** the skill SHALL NOT suggest a run step for it and MAY suggest a read step

#### Scenario: Sources shown only to the author
- **WHEN** the skill presents a PR for confirmation
- **THEN** each bullet and step SHALL show its source, and the PR body that is opened SHALL carry none
