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
SHALL block `gh pr merge` and the merge API endpoint from the moment the skill is invoked.

#### Scenario: Merge attempted after the skill is invoked
- **WHEN** a merge command is attempted in a session where the skill has been invoked
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
