## MODIFIED Requirements

### Requirement: Manual-only PR skill
The toolkit SHALL include a command `jois:write-pr`, the single file
`toolkit/commands/jois/write-pr.md`, that opens GitHub pull requests for the commits on the current
branch. It SHALL declare `disable-model-invocation: true`, so it runs only when the user invokes it by
name and is not listed in the session context. The file SHALL carry the PR guidelines, the PR template
and the verification rules inside it and SHALL be complete when copied by hand. The toolkit SHALL NOT
also ship a `write-pr` skill. The requirements below that say "the skill" apply to this command.

#### Scenario: Not offered unprompted
- **WHEN** a session starts with the command installed
- **THEN** its description SHALL NOT be loaded into the session context and Claude SHALL NOT start it on its own

#### Scenario: Refuses the default branch
- **WHEN** the command is invoked while on `main`
- **THEN** it SHALL open no PR and SHALL tell the user to switch to a feature branch

#### Scenario: Single entry point
- **WHEN** the toolkit is installed
- **THEN** `/jois:write-pr` SHALL exist and no `write-pr` skill SHALL be copied from the toolkit

### Requirement: Author verification is recorded, not invented
The skill SHALL draft Author Verification from the matching OpenSpec `tasks.md` and from the
conversation it runs in. It SHALL NOT state an observed result that no source records. A source is a
`tasks.md` result, a test, build or lint command whose output is visible in the conversation, or the
user's answer. A checked verification task with no recorded result SHALL yield a bullet that names the
check without a result, and the skill SHALL flag it. A task that is not verification SHALL NOT yield a
bullet.

A command run in the conversation SHALL yield a bullet for a group only when it covers a directory the
group's diff changes. It SHALL state only the outcome and counts the output shows. It SHALL NOT be
used as the group's result when a later edit in the conversation touched a file in the group's diff, or
when the run failed; the skill SHALL name such a run to the user instead. A conversation that holds no
usable run, because the session is new or its history is summarized, SHALL contribute nothing.

When no source records verification for a group (no OpenSpec change, no verification task in
`tasks.md`, a task with no recorded result, and no usable run), the skill SHALL first offer to run the
group's documented tests as the next requirement says, and for any group still without a source SHALL
ask the user once, covering every such group, what they ran and saw, before presenting any PR. It SHALL turn the user's
answer into bullets and SHALL NOT add results the user did not give. When the user has none, it SHALL
write that none were recorded.

#### Scenario: Result recorded
- **WHEN** a verification task in `tasks.md` records an observed result
- **THEN** its bullet SHALL carry that result

#### Scenario: Checked task without a result
- **WHEN** a verification task is checked and records no result
- **THEN** its bullet SHALL name the check, SHALL NOT state an outcome, and SHALL be flagged

#### Scenario: Test run seen in the conversation
- **WHEN** the conversation shows `npm test` run in `web/` with its output and the group's diff changes files under `web/`
- **THEN** Author Verification SHALL hold a bullet with that command and the outcome and counts the output shows

#### Scenario: Run covers another directory
- **WHEN** the conversation shows tests run only in `api/` and the group's diff changes only files under `web/`
- **THEN** that run SHALL NOT yield a bullet for the group

#### Scenario: Edited after the run
- **WHEN** a file in the group's diff was edited in the conversation after the test run
- **THEN** the run SHALL NOT be used as the group's result and the skill SHALL tell the user it is out of date

#### Scenario: Failed run
- **WHEN** the latest run of a command in the conversation failed
- **THEN** the skill SHALL NOT report it as a pass and SHALL tell the user it failed

#### Scenario: Fresh or summarized conversation
- **WHEN** the command is run in a new session or the earlier history is summarized
- **THEN** the conversation SHALL contribute no bullet and the skill SHALL use `tasks.md` and the user as before

#### Scenario: Gaps across several groups
- **WHEN** two groups each lack recorded verification from every source
- **THEN** the skill SHALL ask the user once for both and SHALL NOT ask per group

#### Scenario: No OpenSpec change
- **WHEN** the group's commits touch no OpenSpec change and the conversation holds no usable run
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
bullet with its source when it presents the PR (`tasks.md` with or without a recorded result, `chat`,
`repo docs`, `inferred from diff` or `user`), and SHALL NOT include those source tags in the PR body.

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
- **THEN** each bullet and step SHALL show its source, including `chat` for a conversation run, and the PR body that is opened SHALL carry none

### Requirement: The skill never merges
The command SHALL NOT merge a PR, enable auto-merge, or pass `--auto`. A hook declared in the
command's frontmatter SHALL block `gh pr merge` and the merge API endpoint from the moment the
command is invoked.

#### Scenario: Merge attempted after the skill is invoked
- **WHEN** a merge command is attempted in a session where `/jois:write-pr` has been invoked
- **THEN** the hook SHALL block it and the PR SHALL stay open

## ADDED Requirements

### Requirement: Missing tests are offered to the user to run
When a group has no usable verification from any source and its diff changes a directory whose test
command a repository document states, the skill SHALL offer to run that command before it presents any
PR. The offer SHALL cover every such group in a single question that names each command and the
directory it runs in, and the skill SHALL end its turn to wait for the answer. A command SHALL qualify
only under the rules for a run step: stated in a document, every path in it present in the checkout,
no flags added. Only after the user agrees SHALL it run the commands, on the checked-out branch tip
including uncommitted changes, and it SHALL NOT run any command the user did not agree to. A run SHALL
become a `chat` bullet that names the command and states only the outcome and counts its output shows.
A failing, unreadable or timed-out run SHALL be reported to the user, SHALL NOT be fixed by the skill,
SHALL NOT yield a passing bullet and SHALL NOT block the PR.

#### Scenario: Offer for a group with no verification
- **WHEN** a group changes files under `web/`, no source records its verification, and `CLAUDE.md` states `cd web; npm test`
- **THEN** the skill SHALL ask once whether to run that command and SHALL run nothing before the answer

#### Scenario: One question for several groups
- **WHEN** two groups lack verification and each has a documented test command
- **THEN** the skill SHALL put both commands in one question

#### Scenario: User agrees
- **WHEN** the user agrees to the offer
- **THEN** the skill SHALL run the named command, SHALL add a `chat` bullet with the outcome and counts shown, and SHALL NOT ask what the user ran for that group

#### Scenario: User declines
- **WHEN** the user declines the offer
- **THEN** the skill SHALL run nothing and SHALL fall back to asking what the user ran

#### Scenario: No documented command
- **WHEN** the diff changes a directory with no documented test command
- **THEN** the skill SHALL NOT offer to run anything for it and SHALL fall back to asking what the user ran

#### Scenario: Tests fail
- **WHEN** an agreed run fails
- **THEN** the skill SHALL report the failure to the user, SHALL NOT edit code to fix it, SHALL NOT write a passing bullet, and SHALL still allow the PR

#### Scenario: Timed out
- **WHEN** an agreed run exceeds the shell timeout
- **THEN** the skill SHALL treat it as having no result and SHALL tell the user
