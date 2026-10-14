## MODIFIED Requirements

### Requirement: Rules are separated from style
A guideline SHALL be written as a rule ("must" or "never") only if breaking it causes a defect, a security hole, structural damage or code a person cannot readily read. A guideline that only affects consistency or taste is style and SHALL be written as a preference ("prefer"). Readability is a rule, not style, but only for the concrete smells the review skill lists (cryptic names, nested ternaries, dense one-liners that need decoding, functions doing several jobs, comments that restate the code); general judgments such as "feels dense" remain preferences. The core rules SHALL contain rules only. A technology rule MAY carry style, but only in a final "Prefer" section kept separate from its rules. Style that a linter or formatter enforces SHALL NOT appear in any file.

#### Scenario: Core files hold no style
- **WHEN** core-principles or architecture-boundaries is read
- **THEN** every line SHALL be a rule, and no line SHALL be a naming, formatting or layout preference

#### Scenario: Technology style is segregated
- **WHEN** a technology rule contains preferences
- **THEN** they SHALL appear under a "Prefer" heading after all rules

#### Scenario: Readability smells are rules
- **WHEN** the review skill lists a concrete readability smell such as a nested ternary
- **THEN** it SHALL appear under a rule heading and not under "Prefer"

#### Scenario: Subjective readability stays a preference
- **WHEN** a readability judgment has no concrete check, such as "this feels dense"
- **THEN** it SHALL appear only under "Prefer"

### Requirement: Core principles content
The core-principles rule SHALL state, as terse actionable lines: KISS, DRY and YAGNI; code written to be read by a person first (descriptive names, one job per function, no clever constructs that need decoding); single responsibility and layer isolation (business logic does not know HTTP, database drivers or UI); pure logic kept apart from I/O so it can be tested directly; fail fast at boundaries, never swallow errors silently, and handle a failure at the layer that can act on it; idempotent operations and deterministic behavior without hidden global state, including tests that never touch real user state; configuration as data with no hardcoded environment values; additive, backward-compatible evolution of schemas and APIs; running the project's build and type-check before calling a change done; and logging philosophy, including that logs are structured (key/value or JSON) rather than free-form strings.

#### Scenario: Principles are present
- **WHEN** the core-principles rule is read
- **THEN** each of the listed principles SHALL be findable by name

#### Scenario: Readability principle is always-on
- **WHEN** any source-code file is touched
- **THEN** the core-principles rule, which is scoped to source-code types, SHALL already state that code is written to be read by a person first

### Requirement: Architecture boundaries content
The architecture-boundaries rule SHALL state workspace boundaries between frontend, backend and shared code (a backend module does not import frontend code and the reverse); that a data or domain layer does not import web-framework code; that cross-boundary contracts, such as client types mirroring server JSON, live in shared or generated definitions (for example OpenAPI, a shared schema or generated types), that both sides change together, and that a payload shape is never changed on one side only; that a request path carries a correlation ID from the client through every backend hop, and that logs on that path include it; that authorization is enforced on the server and hiding a control in the UI is not security; and that configuration files are validated against a schema at startup with environment-specific values kept separate from code.

#### Scenario: Boundary rule stated
- **WHEN** the architecture-boundaries rule is read
- **THEN** it SHALL forbid backend-to-frontend imports and the reverse, SHALL forbid framework imports in the data layer, SHALL require server-side authorization, and SHALL require schema validation of configuration at startup

#### Scenario: Contract sync stated
- **WHEN** the architecture-boundaries rule is read
- **THEN** it SHALL name at least one mechanism that keeps a cross-language contract in sync and SHALL forbid changing a payload shape on one side only

#### Scenario: Correlation ID stated
- **WHEN** the architecture-boundaries rule is read
- **THEN** it SHALL require a correlation ID to travel with a request from the client through each backend hop and appear in the logs on that path

### Requirement: Review skill is on demand and self-contained
The `coding-standards` skill SHALL be a review checklist (code smells, a blocking readability section, language-agnostic style such as matching surrounding code, clear names, comments that explain why and short functions, and testing structure such as one test file per module) within 4 KB, whose description states it applies to reviewing code quality. Its readability section SHALL list concrete, checkable smells (cryptic names, nested ternaries, dense one-liners that need decoding, functions doing several jobs, comments that restate the code), SHALL report them with the rule-breaking findings, and its "Prefer" list SHALL NOT repeat a guideline already enforced there. It SHALL NOT reference any skill, rule or file that is not in the toolkit, and SHALL NOT carry the technology-specific content owned by the rules.

#### Scenario: No dangling references
- **WHEN** the skill's references to other skills, rules and files are checked
- **THEN** every one SHALL resolve to an item in `toolkit/`

#### Scenario: Skill description is narrow
- **WHEN** the skill's frontmatter is read
- **THEN** its `description` SHALL name code review and quality checks, and SHALL NOT claim to apply to all code

#### Scenario: Readability smell blocks a review
- **WHEN** a reviewed change contains a nested ternary or a cryptic name
- **THEN** the review SHALL list that finding first, with the other rule-breaking findings, and not among the style suggestions

#### Scenario: No duplicate guidance
- **WHEN** the skill's "Prefer" list is read
- **THEN** it SHALL NOT contain "prefer clear code over clever code", which the readability section now owns

## ADDED Requirements

### Requirement: Dependency hygiene in the configuration rule
The configuration rule SHALL require that lockfiles are committed and regenerated with the tool, never hand-edited; that shared packages use no wildcard or floating dependency versions; and that dependencies between packages in the same workspace are declared through the workspace mechanism and not by copying code or by relative path. These lines SHALL stay terse and the rule SHALL stay within the 3 KB technology-rule budget. The rule's `paths:` frontmatter SHALL remain limited to `yml`, `yaml`, `json` and `toml`.

#### Scenario: Dependency lines present
- **WHEN** the configuration rule is read
- **THEN** it SHALL state that lockfiles are committed, that shared packages avoid wildcard or floating versions, and that workspace dependencies use the workspace mechanism

#### Scenario: Scope unchanged
- **WHEN** the `paths:` globs of all technology rules are compared after this change
- **THEN** the configuration rule SHALL still match only `yml`, `yaml`, `json` and `toml`, and no extension SHALL appear in more than one rule

#### Scenario: Rule over budget
- **WHEN** the configuration rule exceeds 3 KB
- **THEN** the docs check SHALL fail and name the file
