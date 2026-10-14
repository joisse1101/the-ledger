## MODIFIED Requirements

### Requirement: Review skill is on demand and self-contained
The `coding-standards` skill SHALL be a review checklist (code smells, a blocking readability section, language-agnostic style such as matching surrounding code, clear names, comments that explain why and short functions, and testing structure such as one test file per module) within 6 KB, whose description states it applies to reviewing code quality. Its readability section SHALL list concrete, checkable smells (cryptic names, nested ternaries, dense one-liners that need decoding, functions doing several jobs, comments that restate the code), SHALL report them with the rule-breaking findings, and its "Prefer" list SHALL NOT repeat a guideline already enforced there. It SHALL end every review by saving it as defined by the review-tracking capability, and any support script it needs for that SHALL live inside the skill's own folder. It SHALL NOT reference any skill, rule or file that is not in the toolkit, and SHALL NOT carry the technology-specific content owned by the rules.

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

#### Scenario: Skill is within its budget
- **WHEN** the docs check runs and the skill file exceeds 6 KB
- **THEN** it SHALL fail and name the file

#### Scenario: Review ends with a saved file
- **WHEN** the skill finishes a review
- **THEN** the review SHALL be saved under `reviews/` and its path reported, not left only in chat

#### Scenario: Skill folder is self-contained
- **WHEN** `toolkit/skills/coding-standards/` is copied by hand into another project
- **THEN** every script the save step needs SHALL be in that folder

## ADDED Requirements

### Requirement: Skills, rules and review commands carry a version
Every skill (`SKILL.md`), every rule file, every agent file, and every command in the `jois-review`
namespace SHALL declare its version inside a `metadata:` map in its frontmatter, as the Agent Skills
format keeps it, with two string keys: `version`, a semantic version `MAJOR.MINOR.PATCH`, and
`last_updated`, the date of the last change as `YYYY-MM-DD`. Both SHALL be bumped by hand whenever
the file's guidance changes. A rule without other frontmatter SHALL still carry a frontmatter block
holding only `metadata:`, and SHALL NOT thereby gain a `paths:` key.

#### Scenario: Version present
- **WHEN** the docs check runs and a skill, rule, agent or `jois-review` command has no `metadata.version`, a `version` that is not `MAJOR.MINOR.PATCH`, or no valid `metadata.last_updated` date
- **THEN** it SHALL fail and name the file

#### Scenario: Top-level version is not accepted
- **WHEN** a file declares `version:` at the top level of its frontmatter instead of under `metadata:`
- **THEN** the docs check SHALL fail and name the file

#### Scenario: Unscoped rule keeps loading everywhere
- **WHEN** `commit-hygiene.md` gains a `metadata:` block
- **THEN** it SHALL still have no `paths:` key and SHALL still load in every session

#### Scenario: Version bumped on change
- **WHEN** a rule's guidance is edited
- **THEN** its `metadata.version` SHALL be raised and `last_updated` set to the date of the edit, so that reviews recorded against the old version are reported stale
