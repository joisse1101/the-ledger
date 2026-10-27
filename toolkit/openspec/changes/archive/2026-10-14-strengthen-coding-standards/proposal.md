## Why

The toolkit's coding standards never say that code must be human readable. The only trace is one
line in the review skill's "Prefer" list ("Prefer clear code over clever code"), which is a
suggestion that is only checked after code is written. The always-on rules that load while code is
being generated are silent on it. Separately, they leave three full-stack gaps: how a cross-language
API contract is kept in sync, how dependencies and lockfiles are managed, and how logs are shaped so
a request can be traced from the UI to the backend.

## What Changes

- Add a readability principle to `core-principles` (code is written to be read by a person first)
  and extend its existing logging line to ask for structured logs.
- Add a blocking "Readability" section to the `coding-standards` review skill with concrete,
  checkable smells (cryptic names, nested ternaries, dense one-liners that need decoding, functions
  doing several jobs, comments that restate the code). Remove the now-duplicate "clear over clever"
  line from its "Prefer" list.
- Add two lines to `architecture-boundaries`: name the mechanisms that keep a cross-language
  contract in sync (OpenAPI, shared schema, generated types) and forbid a one-sided JSON payload
  change; and carry a correlation ID from the client through every backend hop on a request path.
- Add dependency hygiene to `config-files`: commit lockfiles, no wildcard or floating versions in
  shared packages, and declare internal workspace dependencies through the workspace mechanism.
- Every addition is one terse line, to limit the always-on context cost, and stays inside the
  existing size budgets.
- Readability is treated as a rule (a defect when broken), not style. This carves a deliberate
  exception into the "rules are separated from style" requirement, limited to the concrete smells
  listed above.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-coding-standards`: core-principles content gains readability and structured logging;
  architecture-boundaries content gains contract-sync mechanisms and correlation IDs; the technology
  config rule gains dependency hygiene; the review skill gains a blocking readability section; the
  rules-versus-style requirement gains a readability exception.

## Impact

- Files: `toolkit/rules/core-principles.md`, `toolkit/rules/architecture-boundaries.md`,
  `toolkit/rules/config-files.md`, `toolkit/skills/coding-standards/SKILL.md`.
- Spec: delta to `openspec/specs/toolkit-coding-standards/spec.md`.
- Docs: `wiki/Coding-Standards.md` is updated if it restates any changed rule.
- Budgets checked by `api/check_docs.py`: core-principles 2 KB, the two core rules combined 4 KB,
  technology rules 3 KB, skill 4 KB. No budget or checker change is needed.
- Not in scope: `requirements.txt` and `pom.xml` stay outside `config-files` `paths:` (its globs are
  `yml`, `yaml`, `json`, `toml`), so dependency hygiene loads for `package.json`, `pyproject.toml`
  and their lockfiles only. Widening the scope is a separate decision.
