---
name: coding-standards
description: Review checklist for code quality - code smells, naming, comments and test structure. Use when asked to review code, check a change for quality, or clean up a diff. Not needed while writing code; the always-on and per-language rules cover that.
license: MIT
metadata:
  version: "1.1.0"
  last_updated: "2026-10-14"
---

# Code quality review

A checklist for reviewing a change. Findings that break a rule (defects, security, structure) come
first; style findings come last and are suggestions, not blockers. Principles and language mechanics
live in the installed rules (`core-principles`, `architecture-boundaries` and the per-language
rules); check against those rather than restating them here.

## Code smells

- **Long function**: more than one job, or longer than fits on a screen. Split by responsibility.
- **Deep nesting**: three or more levels. Use early returns or extract a function.
- **Magic number or string**: an unexplained literal. Give it a named constant.
- **Duplication**: the same logic in two places. Extract it once the second use is real.
- **Speculative code**: parameters, flags or abstractions nothing uses yet. Remove them.
- **Dead code**: unused functions, imports, branches, commented-out code. Delete it.
- **Hidden coupling**: a function that reads or writes globals, or does I/O, behind a pure-looking name.
- **Swallowed error**: an empty catch or a default that hides a failure.

## Readability

Code a person cannot read at a glance is a rule-breaking finding, listed with the smells above.

- **Cryptic name**: a single letter, an abbreviation or a vague word (`data`, `tmp`, `x`) where a
  descriptive name fits.
- **Nested ternary**: a conditional expression inside another. Use `if` or a named helper.
- **Dense one-liner**: a chain or expression the reader must decode. Split it into named steps.
- **Many jobs in one function**: it needs "and" to describe it. Split by responsibility.
- **Comment restating the code**: it says what the line does, not why. Delete it.

## Testing

- Each test covers one behavior and follows arrange, act, assert.
- A test name says what happens and when (`returns empty list when no match`), not `works`.
- Test behavior through the public interface, not private details.
- One test file per module, placed where the project's convention puts it.
- A bug fix comes with a test that fails without the fix.

## Prefer

These improve consistency and readability. Raise them as suggestions.

- Match the surrounding code's naming, layout and idiom over personal taste.
- Name things for what they are: nouns for values, verb-noun for functions, `is`/`has` for booleans.
- Keep functions short and focused on one job.
- Comment why, not what: the reason for a non-obvious choice, a constraint, a workaround.
- Document public APIs with their contract (inputs, outputs, errors) and no more.

## Save the review

Always save the review as a checklist, so it can be worked through and archived later. Write it to
`reviews/YYYY-MM-DD_HHMM.md` at the repository root (local time; create the folder). If that name
exists, add a suffix (`_HHMM-2`) and never overwrite. Tell the user the path.

Start with this frontmatter:

```yaml
---
reviewed_at: 2026-10-14 17:07
scope: whole codebase | branch name | the diff
commit: <git rev-parse --short HEAD, or none>
status: open
uses:
  - {kind: skill, name: coding-standards, version: "1.1.0", last_updated: "2026-10-14", hash: <hash>}
  - {kind: rule, name: python.md, version: "1.0.0", last_updated: "2026-10-14", hash: <hash>}
---
```

`uses` has one entry for the skill and for every rule you applied. Take each entry's `hash`,
`version` and `last_updated` by running `scripts/Get-ItemHash.ps1 -ItemPath <installed skill folder
or rule file>` (in this skill's folder); never type them from memory.

Then the body, in this order:

1. **Coverage**: what was read and what was not (name skipped areas, such as CSS or generated code).
2. **Findings**, one block each, numbered, ordered rule-breaking first and smells last:

   ```markdown
   ### 3. open-repo reports success when it fails
   - **Category**: Defect
   - **Files**: `api/routes.py:120-134` (`open_repo`)
   - **Problem**: what is wrong and why it matters.
   - **Fix**: the concrete change to make.
   - [ ] Done
   ```

   Category is exactly one of **Rule-breaking**, **Defect**, **Structure**, **Script**, **Smell**.
   Give each location a symbol anchor (function, class or component) beside its line numbers; later
   fixes move lines, the anchor still finds the code.
3. **What's good**: what is already sound, briefly.
