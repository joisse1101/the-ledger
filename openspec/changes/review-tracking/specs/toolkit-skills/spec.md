## ADDED Requirements

### Requirement: Agents source of truth
The repository SHALL keep every custom subagent under `toolkit/agents/`, each entry a single `.md`
file with `name`, `description` and `tools` frontmatter, which is the unit the installer acts on.
The installer SHALL copy agents into Claude Code's agents folder (`~/.claude/agents/` globally,
`<project>/.claude/agents/` per project), with the same named-item selection, no-silent-overwrite,
listing and uninstall behavior as skills, commands and rules, and with the destination coming from
`targets.json`.

#### Scenario: Agent installed globally
- **WHEN** the installer runs with global scope and no item name
- **THEN** `toolkit/agents/code-reviewer.md` SHALL exist in `~/.claude/agents/`

#### Scenario: Drifted agent is not overwritten
- **WHEN** an installed agent differs from the toolkit's and no force option is given
- **THEN** it SHALL be reported as differing and left unchanged

#### Scenario: Uninstall leaves foreign agents alone
- **WHEN** `~/.claude/agents/` holds an agent that is not in the toolkit and uninstall runs
- **THEN** that agent SHALL remain untouched

### Requirement: One content hash shared by installer and reviews
The installer SHALL compute an item's content hash with the same helper that review files use to
record a skill's or rule's hash, so a hash in a review matches the installer's view of the same
item. The helper SHALL be a script shipped inside the `coding-standards` skill folder. The hash
SHALL be unchanged from the installer's existing algorithm (relative paths and file contents in a
stable order), so existing installs are not reported as drifted by this change.

#### Scenario: Hashes agree
- **WHEN** the installer and the review helper hash the same installed rule
- **THEN** both SHALL produce the identical value

#### Scenario: No spurious drift
- **WHEN** an item was up to date before this change and its text is unchanged
- **THEN** the installer SHALL still report it as up to date

### Requirement: Listing shows versions
The installer's status listing SHALL show, for each skill, rule, agent and command item that
declares one, its `version:` from the toolkit and from the destination, alongside the existing
state (missing, up to date, differing).

#### Scenario: Differing item shows both versions
- **WHEN** the installed `python.md` is version 2026-09-01 and the toolkit's is 2026-10-14
- **THEN** the listing SHALL show the item as differing with both versions

#### Scenario: Item without a version
- **WHEN** an item declares no version, such as an OpenSpec-generated command
- **THEN** the listing SHALL show its state without a version and SHALL NOT fail
