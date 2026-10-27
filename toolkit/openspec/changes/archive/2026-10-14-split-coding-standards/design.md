## Context

See proposal.md for motivation. Today `toolkit/skills/coding-standards/SKILL.md` (12.8 KB) is the
only standards artifact in the toolkit. `Install-Toolkit.ps1` handles two item kinds, skills
(folders with a `SKILL.md`) and commands (folders or `.md` files), with destinations read from
`targets.json`. A command item is already "a single `.md` file or a folder", which is the shape
rules need. `api/check_docs.py` enforces size budgets only on `CLAUDE.md` files.

## Goals / Non-Goals

**Goals:**
- Claude loads the guidance for the files it is working on, and a short universal floor always.
- Authors can edit one concern without reading the rest.
- Rules install and uninstall exactly like skills and commands.

**Non-Goals:**
- Changing the root `CLAUDE.md` or `wiki/Coding-Standards.md`. Only the "Local rules" sections of
  `api/CLAUDE.md` and `web/CLAUDE.md` are slimmed.
- Enforcing standards in CI. Linters, formatters and type checkers enforce style; these files carry
  only judgment a tool cannot.
- Supporting tools other than Claude Code.

## Decisions

**Hybrid: rules for file-shaped guidance, a skill for task-shaped guidance.** A skill description is
matched by the model against the request, so "use when editing `.py`" is probabilistic. A rule with
`paths:` frontmatter is attached by file match. Language guidance is file-shaped, so it becomes rules;
"review this code" is task-shaped, so the checklist stays a skill. Alternative considered: all skills
(no installer change, but language rules can be skipped) and all rules (deterministic, but no
on-demand review).

**Rules are single files under `toolkit/rules/`, installed by the existing command-item logic.**
Add a `rules` entry to `targets.json` (`~/.claude/rules`, `.claude/rules`), a `-Rule` parameter and
a third item list in `Install-Toolkit.ps1`. The hash, state, force and uninstall code is reused
unchanged. Alternative: subfolders per rule; rejected as unneeded, and a flat file maps to one name.

**Two unscoped rules, kept tiny.** core-principles (<= 2 KB) and architecture-boundaries
(<= 2 KB, combined <= 4 KB) load at session start in every project, so their size is a recurring
cost. Detail lives in language rules and the review skill. Rationale for splitting the two: core is
language-agnostic code philosophy; architecture is about structure across workspaces and config.

**One owner per topic.** Core says "fail fast, never swallow errors"; the Java rule says only how
(checked vs unchecked exceptions, try-with-resources); Python says bare `except:`; TypeScript says
`unknown` in catch. Language rules link back instead of restating.

**Rules versus style.** A guideline is a rule if breaking it causes a defect, a security hole or
structural damage (server-side authorization, data layer free of framework imports, client types
mirroring server JSON, tests isolated from real user state, no swallowed errors, pure logic apart
from I/O, a single API client wrapper, build before done). It is style if it only affects
consistency (matching surrounding code, naming, why-comments, short functions, one test file per
module, design tokens, colocated CSS, single-source breakpoints). Rules are written as must/never and
live in the always-on and technology rules. Language-agnostic style lives in the review skill as
"prefer" items. Technology-specific style stays in its technology rule under a final "Prefer"
heading, because the skill must not carry technology content. The always-on files hold no style,
which keeps the 2 KB core small and avoids imposing taste on projects that install globally. Source
of the split: the existing `api/CLAUDE.md`, `web/CLAUDE.md` and `wiki/Coding-Standards.md`, whose
generalizable lines were sorted this way; repo-specific names and paths (`isolated_db`,
`tokens.css`, `apiFetch`, `CORSMiddleware`) stay in those files.

**Project files keep only what is specific to the project.** In `api/CLAUDE.md` and `web/CLAUDE.md`
each local rule loses its general principle and keeps the project fact: the `isolated_db` fixture
(not "tests never touch real state"), the `claude_*.py` data-layer path (not "no framework imports"),
`is_local` on delete routes (not "authorize on the server"), `tokens.css`, `breakpoints.ts`,
`apiFetch` and `types.ts` locations, plus lines that are purely local (no `CORSMiddleware`, the
stable `Open-ClaudeRepoWindow.ps1` path, `check_docs.py`, no E2E harness). Each file gains one line
pointing to the toolkit rules for general standards. Alternative: leave the duplication; rejected
because it breaks one owner per topic and the two copies drift.

**Content triage of the existing file.** Moves: TypeScript naming, immutability, async, type
safety, React composition, hooks, state and conditional rendering go to `typescript-react.md`;
input validation and API conventions go to architecture-boundaries (the boundary part) and the
language rules. Stays in the skill: code smells, test structure and naming, comment guidance, and language-agnostic style.
Dropped: generic performance advice (memoization, lazy loading, query tips), the file-layout
section, JSDoc boilerplate, and anything a formatter or linter enforces.

**Config and script rules cover hygiene, not syntax.** `config-files.md` covers schema validation,
no secrets, environment separation, and additive changes. `scripts.md` covers fail-fast flags
(`Set-StrictMode`/`$ErrorActionPreference = 'Stop'`, `set -euo pipefail`), idempotent re-runs,
quoting, and no hardcoded paths.

**Budgets are checked, not trusted.** `check_docs.py` gains a toolkit check: unscoped rules exist
and are within 2 KB / 4 KB combined, each scoped rule has `paths:` and is within 3 KB, the skill is
within 4 KB, and no `paths:` extension appears in two rules. It also verifies that skill references
resolve inside `toolkit/`.

## Risks / Trade-offs

- [Path-scoped rules may load only when a matching file is read, not when a new file is created] →
  verified on Claude Code 2.1.299 in a scratch project: unscoped rules load at session start, and a
  `paths:` rule attaches after reading an existing matching file and after writing a new one. It is
  not loaded before any matching file is touched, so the core rule remains the floor for that case.
- [Global install puts the unscoped rules in every project, which may collide with a project's own
  conventions] → keep the rules terse and non-prescriptive on style, document `-Scope project`, and
  let project `CLAUDE.md` take precedence.
- [`paths:` frontmatter syntax or the rules folder may behave differently across Claude Code
  versions] → confirm the syntax against current documentation during implementation and record the
  version tested in the README.
- [Slimmed project files depend on the rules being installed; a clone on a machine without them
  loses the general guidance] → keep every project fact in the project file, and have the pointer
  line name the install command (`Install-Toolkit.ps1`, optionally `-Scope project`).
- [Existing installs of the old skill show as `differs`] → expected; documented, `-Force` updates.
- [New Java/Python/config content is first-draft, written without a style source of truth] → keep
  each rule short and opinion-light so the owner can edit it; review before archiving.

## Migration Plan

1. Land the installer change and rules together; run `-List` to confirm the state of an existing install.
2. Users run `Install-Toolkit.ps1 -Force -Skill coding-standards` and install the new rules.
3. Rollback: revert the commit and reinstall the previous skill with `-Force`; remove the rules with `-Uninstall -Rule <name>`.
