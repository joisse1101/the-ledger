## ADDED Requirements

### Requirement: Tool-neutral skill source of truth
The repository SHALL keep every custom skill under `toolkit/skills/<name>/`, one folder per skill,
each containing a `SKILL.md` with `name` and `description` frontmatter. The layout SHALL NOT depend
on any one vendor's plugin or marketplace mechanism, and SHALL be usable by copying folders by hand.

#### Scenario: Skill folder is self-contained
- **WHEN** a person copies `toolkit/skills/<name>/` into a tool's skills folder by hand
- **THEN** the skill SHALL be complete without any other file from the repository

#### Scenario: Sample skill ships with the toolkit
- **WHEN** the toolkit is first checked out
- **THEN** at least one sample skill SHALL be present so the install path can be exercised

### Requirement: Documented manual path
`toolkit/README.md` SHALL document a quick start that installs everything, and a separate Skills
section that states which folder each supported tool reads skills from, so the installer is
optional.

#### Scenario: Install without the script
- **WHEN** a reader follows only the Skills section of the README
- **THEN** they SHALL be able to place the skills in the correct folder without running the installer

### Requirement: Install by copy into a global or project scope
The installer SHALL copy skills from `toolkit/skills/` into Claude Code's skills folder: the user's
`~/.claude/skills/` for global scope, or `<project>/.claude/skills/` for project scope. It SHALL
install a single named skill when one is given and every toolkit skill otherwise. Destinations
SHALL come from a data file, not code, so adding a tool is adding an entry.

#### Scenario: Global install of everything
- **WHEN** the installer runs with global scope and no skill name
- **THEN** every skill under `toolkit/skills/` SHALL exist in `~/.claude/skills/`

#### Scenario: Project install of one skill
- **WHEN** the installer runs with project scope, a project path and a skill name
- **THEN** only that skill SHALL be copied to `<project>/.claude/skills/<name>/`

#### Scenario: Unknown skill name
- **WHEN** a skill name is given that is not in `toolkit/skills/`
- **THEN** the installer SHALL fail with a message naming the available skills and copy nothing

### Requirement: No silent overwrite of a differing skill
If a destination skill folder already exists and its contents differ from the toolkit's, the
installer SHALL NOT overwrite it unless explicitly told to, and SHALL report that it differs.

#### Scenario: Drifted copy present
- **WHEN** the destination skill differs from the toolkit's copy and no force option is given
- **THEN** that skill SHALL be left unchanged and reported as differing

#### Scenario: Identical copy present
- **WHEN** the destination skill is identical to the toolkit's
- **THEN** the installer SHALL report it as up to date and change nothing

### Requirement: Status listing and safe uninstall
The installer SHALL be able to list each toolkit skill's state at a destination (missing, up to date,
or differing), and SHALL be able to remove skills, removing only skills that exist in the toolkit
and never any other skill found in the destination.

#### Scenario: Uninstall leaves foreign skills alone
- **WHEN** the destination contains a skill that is not in `toolkit/skills/` and uninstall runs
- **THEN** that skill SHALL remain untouched

### Requirement: Scope limited to skill folders
The installer SHALL write only inside the chosen skills folder and SHALL NOT modify Claude Code
settings, hooks, or any other configuration.

#### Scenario: Settings untouched
- **WHEN** any install or uninstall completes
- **THEN** `settings.json` files SHALL be unchanged
