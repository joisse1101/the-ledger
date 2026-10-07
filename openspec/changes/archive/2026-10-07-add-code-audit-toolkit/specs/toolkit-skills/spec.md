## RENAMED Requirements

- FROM: `### Requirement: Scope limited to skill folders`
- TO: `### Requirement: Scope limited to skills, agents and commands folders`

- FROM: `### Requirement: No silent overwrite of a differing skill`
- TO: `### Requirement: No silent overwrite of a differing item`

## MODIFIED Requirements

### Requirement: Tool-neutral skill source of truth
The repository SHALL keep every custom skill under `toolkit/skills/<name>/`, one folder per skill,
each containing a `SKILL.md` with `name` and `description` frontmatter. It SHALL keep every custom
subagent as `toolkit/agents/<name>.md` and every custom slash command as
`toolkit/commands/<name>.md`. The layout SHALL NOT depend on any one vendor's plugin or marketplace
mechanism, and SHALL be usable by copying files and folders by hand.

#### Scenario: Skill folder is self-contained
- **WHEN** a person copies `toolkit/skills/<name>/` into a tool's skills folder by hand
- **THEN** the skill SHALL be complete without any other file from the repository

#### Scenario: Sample skill ships with the toolkit
- **WHEN** the toolkit is first checked out
- **THEN** it SHALL contain at least one real skill, one agent and one command (no placeholder sample is required) so every install path can be exercised

### Requirement: Documented manual path
`toolkit/README.md` SHALL document a quick start that installs everything, and a separate section
that states which folder each supported tool reads skills, agents and commands from, so the
installer is optional.

#### Scenario: Install without the script
- **WHEN** a reader follows only the manual-install section of the README
- **THEN** they SHALL be able to place the skills, agents and commands in the correct folders without running the installer

### Requirement: Install by copy into a global or project scope
The installer SHALL copy skills, agents and commands from `toolkit/` into Claude Code's matching
folders: the user's `~/.claude/` for global scope, or `<project>/.claude/` for project scope. It
SHALL install a single named item when one is given and everything in the toolkit otherwise.
Destinations SHALL come from a data file, not code, so adding a tool or an item kind is adding an
entry.

#### Scenario: Global install of everything
- **WHEN** the installer runs with global scope and no name
- **THEN** every skill, agent and command under `toolkit/` SHALL exist in the matching folder under `~/.claude/`

#### Scenario: Project install of one skill
- **WHEN** the installer runs with project scope, a project path and a skill name
- **THEN** only that skill SHALL be copied to `<project>/.claude/skills/<name>/`

#### Scenario: Restrict to one kind
- **WHEN** the installer is told to install only agents
- **THEN** only agents SHALL be copied, and skills and commands SHALL be left alone

#### Scenario: Unknown skill name
- **WHEN** a skill name is given that is not in `toolkit/skills/`
- **THEN** the installer SHALL fail with a message naming the available skills and copy nothing

#### Scenario: Unknown agent or command name
- **WHEN** a name is given that matches no skill, agent or command in `toolkit/`
- **THEN** the installer SHALL fail with a message naming the available items and copy nothing

### Requirement: No silent overwrite of a differing item
If a destination skill folder, agent file or command file already exists and its contents differ
from the toolkit's, the installer SHALL NOT overwrite it unless explicitly told to, and SHALL
report that it differs.

#### Scenario: Drifted copy present
- **WHEN** the destination item differs from the toolkit's copy and no force option is given
- **THEN** that item SHALL be left unchanged and reported as differing

#### Scenario: Identical copy present
- **WHEN** the destination item is identical to the toolkit's
- **THEN** the installer SHALL report it as up to date and change nothing

### Requirement: Status listing and safe uninstall
The installer SHALL be able to list each toolkit skill's, agent's and command's state at a
destination (missing, up to date, or differing), and SHALL be able to remove items, removing only
items that exist in the toolkit and never any other skill, agent or command found in the
destination.

#### Scenario: Uninstall leaves foreign skills alone
- **WHEN** the destination contains a skill that is not in `toolkit/skills/` and uninstall runs
- **THEN** that skill SHALL remain untouched

#### Scenario: Uninstall leaves foreign agents and commands alone
- **WHEN** the destination contains an agent or command that is not in `toolkit/` and uninstall runs
- **THEN** that agent or command SHALL remain untouched

### Requirement: Scope limited to skills, agents and commands folders
The installer SHALL write only inside the chosen skills, agents and commands folders and SHALL NOT
modify Claude Code settings, hooks, or any other configuration.

#### Scenario: Settings untouched
- **WHEN** any install or uninstall completes
- **THEN** `settings.json` files SHALL be unchanged
