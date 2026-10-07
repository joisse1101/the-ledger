## MODIFIED Requirements

### Requirement: Status listing and safe uninstall
The installer SHALL be able to list each toolkit skill's, agent's and command's state in both the
global and the project scope at once (missing, up to date, or differing), and SHALL mark an item
present in both scopes as identical or as shadowed (the project copy takes precedence and differs).
It SHALL report, per scope, whether the `/code-audit` set (its skill, both agents and its command) is
complete, incomplete (naming what is missing) or absent. It SHALL be able to remove items, removing
only items that exist in the toolkit and never any other skill, agent or command found in the
destination, and SHALL ask for confirmation before removing unless told to proceed.

#### Scenario: Both scopes shown together
- **WHEN** the installer lists status with a project folder that has some toolkit items and a global
  scope that has all of them
- **THEN** each item SHALL show its global state and its project state side by side

#### Scenario: Project copy shadows a differing global copy
- **WHEN** an item exists in both scopes and the two copies differ
- **THEN** the listing SHALL flag that the project copy shadows the global one

#### Scenario: Identical copies in both scopes
- **WHEN** an item exists in both scopes with identical contents
- **THEN** the listing SHALL show it as present in both and the same

#### Scenario: Incomplete code-audit set
- **WHEN** a scope holds the code-audit skill and command but not one of its agents
- **THEN** the listing SHALL report that scope as incomplete and name the missing agent

#### Scenario: No project given
- **WHEN** no project folder is given and the current directory is not inside a git repository
- **THEN** the project column SHALL be shown as not applicable and the global column SHALL still be shown

#### Scenario: Uninstall leaves foreign skills alone
- **WHEN** the destination contains a skill that is not in `toolkit/skills/` and uninstall runs
- **THEN** that skill SHALL remain untouched

#### Scenario: Uninstall leaves foreign agents and commands alone
- **WHEN** the destination contains an agent or command that is not in `toolkit/` and uninstall runs
- **THEN** that agent or command SHALL remain untouched

#### Scenario: Uninstall asks first
- **WHEN** uninstall is requested without a name and without an option to proceed unprompted
- **THEN** the installer SHALL ask for confirmation and SHALL remove nothing if it is declined

## ADDED Requirements

### Requirement: Post-install verification
After installing, the installer SHALL verify the result: it SHALL check that the installed set is
complete for the scope it wrote to, and SHALL run the installed audit engine against a temporary git
repository to confirm it launches and produces output, then remove that temporary repository. The
check SHALL NOT write to the user's repositories or to `~/.claude` beyond the install itself, and it
SHALL end with a summary naming the scope, the counts installed, updated, skipped and unchanged, the
verification result, and that Claude Code must be restarted to pick the items up.

#### Scenario: Healthy install
- **WHEN** a full install completes and Python and git work
- **THEN** the installer SHALL report the set complete and the engine smoke test passed

#### Scenario: Engine does not launch
- **WHEN** the installed engine fails to run in the temporary repository
- **THEN** the installer SHALL report the verification as failed with the reason, and SHALL exit non-zero

#### Scenario: Partial install flagged
- **WHEN** only some of the code-audit items were installed into a scope
- **THEN** the installer SHALL warn that `/code-audit` will not work until the rest are installed

#### Scenario: Project install reminder
- **WHEN** the install scope is a project
- **THEN** the summary SHALL state that `.claude/` was written into that project and should be committed or ignored

### Requirement: Preflight warnings
Before acting, the installer SHALL check that git, a Python 3 interpreter that actually runs, and a
POSIX shell are available, and SHALL warn about each that is not. A warning SHALL NOT stop the
install.

#### Scenario: Python alias is a stub
- **WHEN** a `python` command exists on the path but fails to run
- **THEN** the installer SHALL warn that Python is unusable and continue

#### Scenario: Everything present
- **WHEN** git, Python and a shell all run
- **THEN** the installer SHALL print no preflight warning

### Requirement: Overridable global destination
The installer SHALL accept an option that replaces the user's home Claude folder as the global
destination, so installs, listings and tests can run against a throwaway folder. Without it, the
global destination SHALL be `~/.claude/` as before.

#### Scenario: Sandboxed global install
- **WHEN** the installer runs with global scope and the override pointing at a temporary folder
- **THEN** items SHALL be written under that folder and nothing under the real `~/.claude/` SHALL change
