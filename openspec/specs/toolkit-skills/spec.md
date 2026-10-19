# toolkit-skills Specification

## Purpose

Keeps reusable AI-agent skills, slash commands and rules in one tool-neutral place in the repo and installs them by copy into a tool's skills, commands and rules folders, globally or per project, without silently overwriting a differing copy.

## Requirements

### Requirement: Tool-neutral skill source of truth
The repository SHALL keep every custom skill under `toolkit/skills/<name>/`, one folder per skill,
each containing a `SKILL.md` with `name` and `description` frontmatter. The layout SHALL NOT depend
on any one vendor's plugin or marketplace mechanism, and SHALL be usable by copying folders by hand.

#### Scenario: Skill folder is self-contained
- **WHEN** a person copies `toolkit/skills/<name>/` into a tool's skills folder by hand
- **THEN** the skill SHALL be complete without any other file from the repository

### Requirement: Slash commands source of truth
The repository SHALL keep every custom slash command under `toolkit/commands/`. Each entry directly
under it SHALL be either a single `.md` file or a folder of `.md` files used as a namespace, and is
the unit the installer acts on.

#### Scenario: Namespace folder is one unit
- **WHEN** `toolkit/commands/opsx/` holds several command files
- **THEN** the installer SHALL treat `opsx` as one command item and copy the whole folder

### Requirement: Rules source of truth
The repository SHALL keep every custom Claude Code rule under `toolkit/rules/`. Each entry directly
under it SHALL be a single `.md` file, optionally with `paths:` frontmatter limiting it to matching
files, and is the unit the installer acts on.

#### Scenario: Rule file is one unit
- **WHEN** `toolkit/rules/java.md` exists
- **THEN** the installer SHALL treat `java.md` as one rule item and copy that file

### Requirement: Documented manual path
`toolkit/README.md` SHALL document a quick start that installs everything, and a separate section
stating which folders each supported tool reads skills and commands from, so the installer is
optional.

#### Scenario: Install without the script
- **WHEN** a reader follows only the manual-install section of the README
- **THEN** they SHALL be able to place the skills and commands in the correct folders without running the installer

### Requirement: Install by copy into a global or project scope
The installer SHALL copy skills from `toolkit/skills/` into Claude Code's skills folder, commands
from `toolkit/commands/` into its commands folder, and rules from `toolkit/rules/` into its rules
folder: the user's `~/.claude/skills/`, `~/.claude/commands/` and `~/.claude/rules/` for global
scope, or `<project>/.claude/skills/`, `<project>/.claude/commands/` and `<project>/.claude/rules/`
for project scope. It SHALL install only the named skill, command item and/or rule when given and
everything otherwise. Destinations SHALL come from a data file, not code, so adding a tool is
adding an entry.

#### Scenario: Global install of everything
- **WHEN** the installer runs with global scope and no item name
- **THEN** every skill under `toolkit/skills/` SHALL exist in `~/.claude/skills/`, every command item under `toolkit/commands/` SHALL exist in `~/.claude/commands/`, and every rule under `toolkit/rules/` SHALL exist in `~/.claude/rules/`

#### Scenario: Project install of named items
- **WHEN** the installer runs with project scope, a project path and a skill, command and/or rule name
- **THEN** only those items SHALL be copied under `<project>/.claude/`

#### Scenario: Unknown name
- **WHEN** a skill, command or rule name is given that is not in the toolkit
- **THEN** the installer SHALL fail with a message naming the available items and copy nothing

### Requirement: No silent overwrite of a differing item
If a destination skill, command item or rule already exists and its contents differ from the
toolkit's, the installer SHALL NOT overwrite it unless explicitly told to, and SHALL report that it
differs.

#### Scenario: Drifted copy present
- **WHEN** the destination item differs from the toolkit's copy and no force option is given
- **THEN** that item SHALL be left unchanged and reported as differing

#### Scenario: Identical copy present
- **WHEN** the destination item is identical to the toolkit's
- **THEN** the installer SHALL report it as up to date and change nothing

### Requirement: Status listing and safe uninstall
The installer SHALL be able to list each toolkit item's state at a destination (missing, up to date,
or differing), and SHALL be able to remove items, removing only items that exist in the toolkit and
never any other skill, command or rule found in the destination.

#### Scenario: Uninstall leaves foreign items alone
- **WHEN** the destination contains a skill, command or rule that is not in the toolkit and uninstall runs
- **THEN** that item SHALL remain untouched

### Requirement: Scope limited to skill, command and rule folders
The installer SHALL write only inside the chosen skills, commands and rules folders and SHALL NOT
modify Claude Code settings, hooks, or any other configuration.

#### Scenario: Settings untouched
- **WHEN** any install or uninstall completes
- **THEN** `settings.json` files SHALL be unchanged

### Requirement: Commands stay out of the session context
Every command file under `toolkit/commands/`, including the `opsx` set, SHALL declare
`disable-model-invocation: true` in its frontmatter, so its description is not loaded into a new
session's skill listing while the user can still invoke it by name. Skills, including
`coding-standards`, SHALL NOT be given this flag by this requirement. The docs check SHALL fail and
name any command file without the flag.

#### Scenario: Command is hidden but runnable
- **WHEN** a new session starts with the commands installed
- **THEN** no command description SHALL appear in `/context`, and typing `/jois:stage` SHALL still run it

#### Scenario: Flag is missing
- **WHEN** a command file under `toolkit/commands/` lacks the flag
- **THEN** the docs check SHALL fail and name the file

#### Scenario: Skill stays discoverable
- **WHEN** a session starts with `coding-standards` installed
- **THEN** its description SHALL still be listed

### Requirement: Jois commands carry a version
Each command file under `toolkit/commands/jois/` SHALL declare `metadata.version` (semver) and
`metadata.last_updated` (a date) in its frontmatter, and the docs check SHALL fail and name a file
where either is missing or malformed. The generated `opsx` commands are exempt.

#### Scenario: Missing version
- **WHEN** `toolkit/commands/jois/stage.md` has no `metadata.version`
- **THEN** the docs check SHALL fail and name the file

#### Scenario: Opsx commands exempt
- **WHEN** `toolkit/commands/opsx/apply.md` has no `metadata.last_updated`
- **THEN** the docs check SHALL NOT report it for that reason

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

### Requirement: The skill never merges
The command SHALL NOT merge a PR, enable auto-merge, or pass `--auto`. A hook declared in the
command's frontmatter SHALL block `gh pr merge` and the merge API endpoint from the moment the
command is invoked.

#### Scenario: Merge attempted after the skill is invoked
- **WHEN** a merge command is attempted in a session where `/jois:write-pr` has been invoked
- **THEN** the hook SHALL block it and the PR SHALL stay open

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
