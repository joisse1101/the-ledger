## Purpose

Gives a developer one `/code-audit` command that checks a branch for quality, security and architecture problems, running deterministic tools first and using subagents only over their recorded evidence.

## ADDED Requirements

### Requirement: Single entry point with two phases
The toolkit SHALL provide a `/code-audit` command that runs Phase 0 (quality gate) and then Phase 1 (security and health) from one invocation, and ends by presenting one consolidated report.

#### Scenario: Both phases run in order
- **WHEN** a user runs `/code-audit` and Phase 0 finds no blocking errors
- **THEN** Phase 1 SHALL run after Phase 0 and a single report SHALL be presented at the end

### Requirement: Phase 0 stops only on syntax and type errors
Phase 0 SHALL detect which languages the audited repository uses and run the matching linters and type checkers. A syntax error or type-check failure SHALL stop the audit before Phase 1 and before any subagent is started. Lint and style findings SHALL NOT stop the audit; they SHALL be carried into the report.

#### Scenario: Syntax error stops the audit
- **WHEN** Phase 0 finds a syntax or type error
- **THEN** the audit SHALL stop, report those errors, and run no Phase 1 scanner and no subagent

#### Scenario: Style findings do not stop the audit
- **WHEN** Phase 0 finds only lint or style findings
- **THEN** Phase 1 SHALL still run and those findings SHALL appear in the report

#### Scenario: Language not present
- **WHEN** the repository contains no files for a language
- **THEN** that language's tools SHALL NOT be run or reported as skipped

### Requirement: Default scope is the diff, with a full-scan option
By default the audit SHALL examine only files changed relative to the `main` branch. A `--full` option SHALL make it examine the whole repository.

#### Scenario: Default diff scope
- **WHEN** a user runs `/code-audit` with no options
- **THEN** only files changed against `main` SHALL be scanned and reviewed

#### Scenario: Full scan
- **WHEN** a user runs `/code-audit --full`
- **THEN** every tracked file in the repository SHALL be in scope

#### Scenario: Nothing changed
- **WHEN** the default scope contains no changed files
- **THEN** the audit SHALL say there is nothing to audit and suggest `--full`

### Requirement: Deterministic evidence before any LLM review
Phase 1 SHALL run the available scanners (secrets, static security, duplicate code, dependency vulnerabilities) and write each one's output as a structured JSON file in a per-run evidence folder outside the audited repository before any subagent starts. Subagents SHALL be given those files as their evidence.

#### Scenario: Evidence files exist before agents run
- **WHEN** a subagent is started
- **THEN** the JSON evidence files for every scanner that ran SHALL already exist in the evidence folder, and that folder SHALL NOT be inside the audited repository

#### Scenario: Findings trace to a scanner or a file
- **WHEN** a finding appears in the report
- **THEN** it SHALL cite either the scanner and rule that produced it, or the file and line a subagent reviewed

### Requirement: Audit never modifies the audited repository
The audit SHALL NOT create, change or delete any file in the audited repository, nor change git state (index, branches, stash, config). This SHALL be enforced by mechanisms that do not depend on the model following instructions: subagents SHALL be restricted to read-only tools and SHALL be blocked from any write or command execution; scanners and linters SHALL run in report-only mode with every auto-fix option off; and the audit SHALL compare the repository's state before and after the run.

#### Scenario: Subagent cannot write
- **WHEN** a subagent attempts to edit or write a file, or run a shell command
- **THEN** the attempt SHALL be blocked and no file SHALL change

#### Scenario: Scanners never auto-fix
- **WHEN** a linter or scanner offers an auto-fix mode
- **THEN** the audit SHALL run it with that mode off

#### Scenario: Tampering detected
- **WHEN** the repository's tracked files, untracked files or git state differ after the audit from before it
- **THEN** the audit SHALL report a failure naming the changed paths and SHALL NOT present the run as clean

#### Scenario: Clean repo stays clean
- **WHEN** an audit completes normally
- **THEN** the repository's working tree and git state SHALL be identical to before the audit

### Requirement: Missing tools are skipped, not fatal
When a scanner, linter or type checker is not installed, the audit SHALL record it as skipped with the tool's name, SHALL continue with the remaining tools, and SHALL list every skipped tool in the report. The audit SHALL NOT install tools.

#### Scenario: Scanner not installed
- **WHEN** a Phase 1 scanner is not installed
- **THEN** the audit SHALL continue, and the report SHALL state that this tool was skipped because it is not installed

### Requirement: Focused security and architecture subagents
The audit SHALL run a security subagent and an architecture subagent in isolated contexts. The security subagent SHALL correlate scanner evidence with OWASP-style data-flow review and remove false positives. The architecture subagent SHALL review duplication evidence and complex files for KISS, YAGNI and DRY violations and propose a concrete refactor for each. Neither subagent SHALL be given the whole repository to read.

#### Scenario: False positive filtered
- **WHEN** the security subagent judges a scanner finding to be a false positive
- **THEN** the finding SHALL be removed from the triage and listed as dismissed with a one-line reason

#### Scenario: Actionable refactor
- **WHEN** the architecture subagent reports a violation
- **THEN** the finding SHALL include the file, the principle violated, and a proposed refactor

### Requirement: Severity baseline with justified adjustment
Each finding SHALL start with the severity its scanner assigned, mapped to Critical, Medium or Low. A subagent MAY raise or lower it, and SHALL give a one-line reason for each change, which the report SHALL show.

#### Scenario: Severity downgraded
- **WHEN** a subagent lowers a finding's severity
- **THEN** the report SHALL show the original severity, the new severity and the reason

### Requirement: Consolidated triage report
The audit SHALL end with a single report that groups findings as Critical (blockers), Medium (refactor) and Low (tech debt), each with location, source and suggested fix, followed by the list of skipped tools and the audit's scope.

#### Scenario: Clean audit
- **WHEN** no findings remain after triage
- **THEN** the report SHALL say so and still list the scope and any skipped tools
