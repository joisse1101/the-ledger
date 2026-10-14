---
name: coding-standards
description: Review checklist for code quality - code smells, naming, comments and test structure. Use when asked to review code, check a change for quality, or clean up a diff. Not needed while writing code; the always-on and per-language rules cover that.
license: MIT
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
- Comment why, not what: the reason for a non-obvious choice, a constraint, a workaround. Delete a
  comment that restates the code.
- Document public APIs with their contract (inputs, outputs, errors) and no more.
- Prefer clear code over clever code.
