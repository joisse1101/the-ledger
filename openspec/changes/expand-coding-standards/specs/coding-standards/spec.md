## Purpose

Provides one versioned, citable set of coding standards across the languages and file formats the projects use, so reviews and audits can point at a specific rule and know whether a tool or a human judgment enforces it.

## ADDED Requirements

### Requirement: Standards shipped as a toolkit skill
The standards SHALL be a skill at `toolkit/skills/coding-standards/` with a `SKILL.md` and reference files, self-contained so the folder can be copied by hand. `SKILL.md` SHALL stay short and SHALL direct the reader to load only the reference files relevant to the code at hand.

#### Scenario: Only relevant rules loaded
- **WHEN** the standards are applied to a Python file
- **THEN** only the general principles, the structure file and the Python reference file SHALL need to be read

#### Scenario: Self-contained folder
- **WHEN** the skill folder is copied alone into a skills folder
- **THEN** it SHALL work without any other file from the repository

### Requirement: Coverage of the project's languages and formats
The standards SHALL provide a reference file for each of: Python, TypeScript with React, SQL, HTML, nginx configuration, Dockerfile and docker-compose, and PowerShell. A language-neutral structure file SHALL cover file organization and separation of concerns.

#### Scenario: Each language has a file
- **WHEN** the skill is inspected
- **THEN** a reference file SHALL exist for every language and format listed above, plus the structure file

### Requirement: Citable rule format
Every rule SHALL have a unique, stable ID of the form `CS-<AREA>-<NNN>`, the rule text, an enforced-by field, a severity, and a short example of compliant and non-compliant code. IDs SHALL NOT be reused or renumbered once published.

#### Scenario: Rule is citable
- **WHEN** a finding references a standards rule
- **THEN** the rule's ID SHALL resolve to exactly one rule in the reference files

#### Scenario: Retired rule
- **WHEN** a rule is removed
- **THEN** its ID SHALL be marked retired and SHALL NOT be assigned to a new rule

### Requirement: Enforcement is declared per rule
The enforced-by field SHALL name either a specific tool and its rule identifier, or the value "judgment". A rule enforced by a tool SHALL also say what it falls back to when that tool is not installed, which SHALL be judgment review.

#### Scenario: Tool-enforced rule
- **WHEN** a rule is enforceable by Ruff, ESLint, tsc, mypy, PSScriptAnalyzer, hadolint, `docker compose config` or sqlfluff
- **THEN** its enforced-by field SHALL name that tool and the specific rule or check

#### Scenario: Tool missing
- **WHEN** the tool a rule names is not installed
- **THEN** the rule SHALL still apply as a judgment rule and SHALL be reported as not machine-checked

#### Scenario: No tool exists
- **WHEN** no practical tool exists for a rule (for example nginx or HTML conventions)
- **THEN** the rule SHALL be written with enforced-by "judgment"

### Requirement: Style and security hardening in scope
Each language or format reference SHALL contain both style and readability rules and security-hardening rules appropriate to it, such as parameterized queries for SQL, strict mode for PowerShell, non-root and pinned images for Docker, and security headers and TLS settings for nginx.

#### Scenario: Hardening rules present
- **WHEN** a reference file for SQL, PowerShell, Docker or nginx is read
- **THEN** it SHALL contain at least one security-hardening rule

### Requirement: Structure rules with checkable limits
The structure file SHALL state separation-of-concerns and layering principles, and SHALL define numeric limits for file length, function length, nesting depth and the absence of import cycles. The limits SHALL be stated as data a script can read, separate from the explanatory text.

#### Scenario: Limits are machine-readable
- **WHEN** a script reads the structure limits
- **THEN** it SHALL obtain each numeric limit without parsing prose

#### Scenario: Principles are judgment
- **WHEN** a structure rule has no numeric form (such as "one module per concern")
- **THEN** it SHALL be marked judgment

### Requirement: Precedence of project standards
When a repository defines its own coding standards, those SHALL take precedence over a language reference file, which SHALL take precedence over the general principles. A conflict SHALL be resolved in that order and the overriding source SHALL be named.

#### Scenario: Repo overrides baseline
- **WHEN** a repository's own standards disagree with a language reference rule
- **THEN** the repository's standard SHALL apply and the finding or review SHALL say so

### Requirement: No dependence on unavailable skills
The standards SHALL NOT reference skills, rule files or tools that are not part of the toolkit or declared as optional, and SHALL NOT use framework-specific examples (such as Next.js or Supabase) as general rules.

#### Scenario: Links resolve
- **WHEN** the skill's files are checked for references to other skills or files
- **THEN** every reference SHALL resolve within the toolkit or be a declared optional tool
