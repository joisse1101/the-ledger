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
