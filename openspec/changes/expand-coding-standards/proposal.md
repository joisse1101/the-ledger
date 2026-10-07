## Why

The only shared coding standard is a global `coding-standards` skill that lives outside the repo, is almost entirely TypeScript, React and Next.js, links to skills that do not exist, and states rules as prose that nothing can check. The repo is Python, TypeScript, PowerShell, Docker and nginx. The planned `/code-audit` needs standards it can cite and enforce, not general advice.

## What Changes

- Add a `coding-standards` skill to `toolkit/skills/`, so it is versioned and installed with the rest of the toolkit. It has a short `SKILL.md` and per-topic reference files loaded only when relevant: Python, TypeScript/React, SQL, HTML, nginx, Docker and docker-compose, PowerShell, and a language-neutral structure file.
- Every rule is a stable, citable record: an ID (for example `CS-PY-007`), the rule, who enforces it (a named tool and its rule, or "judgment"), and a short good and bad example.
- Rules cover style and security hardening for each language or format. Structure rules cover separation of concerns and layering as principles, plus measurable limits (file length, function length, nesting depth, import cycles).
- Precedence is explicit: a repository's own standards (such as `wiki/Coding-Standards.md`) override a language file, which overrides the general principles.
- Map rules to optional enforcement tools where one exists: Ruff and mypy, ESLint and tsc, PSScriptAnalyzer, hadolint, `docker compose config -q` and sqlfluff. Rules with no tool (nginx, HTML and others) are written as judgment rules for the audit's subagents. A tool-enforced rule whose tool is not installed degrades to a judgment rule and is reported as such.
- Replace the unmaintainable parts of the current global skill (Next.js and Supabase examples, dead references) rather than copying them.

## Capabilities

### New Capabilities
- `coding-standards`: the structure, rule format, coverage, precedence and enforcement mapping of the shared coding standards.

### Modified Capabilities

None in this change. The `code-audit` capability (from `add-code-audit-toolkit`, not yet archived) needs a follow-up delta once archived: add PSScriptAnalyzer, hadolint, `docker compose config` and sqlfluff to its tool set, and require findings to cite a standards rule ID when one applies. This is tracked as a task so it is not forgotten.

## Impact

- **New files:** `toolkit/skills/coding-standards/` (`SKILL.md`, `languages/*.md`, `structure.md`, `tools.md`).
- **Changed later (after both changes land):** `toolkit/skills/code-audit/` tool table and agents' citation rule; `toolkit/README.md`, `CLAUDE.md` and `wiki/Repository-Layout.md` mentions.
- **Install conflict:** the installer will report the user's existing global `coding-standards` as `differs` and leave it unchanged unless `-Force` is used. Replacing it is an explicit user choice.
- **Dependencies:** none added. All enforcement tools stay optional and are skipped if missing.
- **Ordering:** built after `add-code-audit-toolkit`; the audit works without it using its current baseline.
