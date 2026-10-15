## ADDED Requirements

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
- **WHEN** `toolkit/commands/jois/apply.md` has no `metadata.version`
- **THEN** the docs check SHALL fail and name the file

#### Scenario: Opsx commands exempt
- **WHEN** `toolkit/commands/opsx/apply.md` has no `metadata.last_updated`
- **THEN** the docs check SHALL NOT report it for that reason
