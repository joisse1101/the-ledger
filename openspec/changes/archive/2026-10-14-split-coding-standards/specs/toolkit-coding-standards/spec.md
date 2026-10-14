## Purpose

Defines how the toolkit's coding standards are layered so that Claude loads only the guidance that matches the work: a small always-on floor, structural boundaries, per-technology rules scoped to file types, and an on-demand review checklist.

## ADDED Requirements

### Requirement: Layered standards
The toolkit SHALL provide its coding standards as separate files, not one document: a core-principles rule, an architecture-boundaries rule, one rule per technology (TypeScript/React, Java, Python, configuration files, scripts), and a `coding-standards` review skill. No file SHALL duplicate another's guidance; a rule SHALL link to the layer that owns a topic instead of restating it.

#### Scenario: Each layer exists as its own file
- **WHEN** a reader lists `toolkit/rules/` and `toolkit/skills/`
- **THEN** they SHALL find core-principles, architecture-boundaries, typescript-react, java, python, config-files and scripts rules and a `coding-standards` skill, each as a separate file

#### Scenario: Topic has one owner
- **WHEN** a principle such as fail-fast error handling is covered by the core rule
- **THEN** language rules SHALL add only language-specific mechanics for it and SHALL NOT restate the principle

### Requirement: Always-on floor is small
The core-principles and architecture-boundaries rules SHALL have no `paths:` frontmatter, so they apply to all work, and SHALL together stay within 4 KB, with core-principles within 2 KB.

#### Scenario: Always-on rules within budget
- **WHEN** the docs check runs
- **THEN** it SHALL fail if either unscoped rule is missing, if their combined size exceeds 4 KB, or if core-principles exceeds 2 KB

### Requirement: Technology rules are path-scoped
Each technology rule SHALL declare `paths:` frontmatter matching only its own file types, so it loads when files of that type are in play and not otherwise: TypeScript/React for `ts`, `tsx`, `js`, `jsx`, `css` and `html`; Java for `java`; Python for `py`; configuration for `yml`, `yaml`, `json` and `toml`; scripts for `ps1`, `sh` and `bat`. Each such rule SHALL stay within 3 KB.

#### Scenario: TypeScript/React rules and preferences
- **WHEN** the TypeScript/React rule is read
- **THEN** it SHALL require calling the backend only through a single API client wrapper, and design tokens for colors, colocated component styles, single-source breakpoints and size-independent data in views SHALL appear only under its "Prefer" heading

#### Scenario: Patterns do not overlap
- **WHEN** the `paths:` globs of all technology rules are compared
- **THEN** no file extension SHALL appear in more than one rule

#### Scenario: Rule over budget
- **WHEN** a technology rule exceeds 3 KB
- **THEN** the docs check SHALL fail and name the file

### Requirement: Rules are separated from style
A guideline SHALL be written as a rule ("must" or "never") only if breaking it causes a defect, a security hole or structural damage. A guideline that only affects consistency or readability is style and SHALL be written as a preference ("prefer"). Always-on rules SHALL contain rules only. A technology rule MAY carry style, but only in a final "Prefer" section kept separate from its rules. Style that a linter or formatter enforces SHALL NOT appear in any file.

#### Scenario: Always-on files hold no style
- **WHEN** core-principles or architecture-boundaries is read
- **THEN** every line SHALL be a rule, and no line SHALL be a naming, formatting or layout preference

#### Scenario: Technology style is segregated
- **WHEN** a technology rule contains preferences
- **THEN** they SHALL appear under a "Prefer" heading after all rules

### Requirement: Core principles content
The core-principles rule SHALL state, as terse actionable lines: KISS, DRY and YAGNI; single responsibility and layer isolation (business logic does not know HTTP, database drivers or UI); pure logic kept apart from I/O so it can be tested directly; fail fast at boundaries, never swallow errors silently, and handle a failure at the layer that can act on it; idempotent operations and deterministic behavior without hidden global state, including tests that never touch real user state; configuration as data with no hardcoded environment values; additive, backward-compatible evolution of schemas and APIs; running the project's build and type-check before calling a change done; and logging philosophy.

#### Scenario: Principles are present
- **WHEN** the core-principles rule is read
- **THEN** each of the listed principles SHALL be findable by name

### Requirement: Architecture boundaries content
The architecture-boundaries rule SHALL state workspace boundaries between frontend, backend and shared code (a backend module does not import frontend code and the reverse); that a data or domain layer does not import web-framework code; that cross-boundary contracts, such as client types mirroring server JSON, live in shared or generated definitions and both sides change together; that authorization is enforced on the server and hiding a control in the UI is not security; and that configuration files are validated against a schema at startup with environment-specific values kept separate from code.

#### Scenario: Boundary rule stated
- **WHEN** the architecture-boundaries rule is read
- **THEN** it SHALL forbid backend-to-frontend imports and the reverse, SHALL forbid framework imports in the data layer, SHALL require server-side authorization, and SHALL require schema validation of configuration at startup

### Requirement: Review skill is on demand and self-contained
The `coding-standards` skill SHALL be a review checklist (code smells, language-agnostic style such as matching surrounding code, clear names, comments that explain why and short functions, and testing structure such as one test file per module) within 4 KB, whose description states it applies to reviewing code quality. It SHALL NOT reference any skill, rule or file that is not in the toolkit, and SHALL NOT carry the technology-specific content owned by the rules.

#### Scenario: No dangling references
- **WHEN** the skill's references to other skills, rules and files are checked
- **THEN** every one SHALL resolve to an item in `toolkit/`

#### Scenario: Skill description is narrow
- **WHEN** the skill's frontmatter is read
- **THEN** its `description` SHALL name code review and quality checks, and SHALL NOT claim to apply to all code
