## Context

Today `~/.claude/skills/coding-standards/SKILL.md` (about 13 KB) is a single file of TypeScript, React and Next.js examples with prose rules, and it points at skills (`frontend-patterns`, `backend-patterns`, `rules/common/coding-style.md`) that do not exist here. `wiki/Coding-Standards.md` is a separate, short, repo-specific page. The toolkit installer copies skill folders and reports a differing copy rather than overwriting it. See proposal.md for motivation.

The planned `/code-audit` (change `add-code-audit-toolkit`) has a read-only `arch-checker` limited to Read, Grep and Glob, and requires findings to cite evidence. Nothing in this repo has `.sql` files; SQL appears only as strings in Python. The `gateway/` folder has a Dockerfile, a compose file and an nginx config template.

## Goals / Non-Goals

**Goals:**
- Rules the audit and a reviewer can cite by ID, with who enforces each stated.
- Cover Python, TypeScript/React, SQL, HTML, nginx, Docker and compose, PowerShell, and structure.
- Let a tool take over any rule it can enforce, so the LLM only judges the rest.
- Keep the skill small to load: relevant files only.

**Non-Goals:**
- Writing the tool configs (Ruff, ESLint and so on) for every repo. Standards name tool rules; each repo owns its config.
- Framework playbooks beyond React basics.
- Changing `/code-audit` itself in this change (see task 5.1).
- Auto-fixing or rewriting code.

## Decisions

### D1. Layout: small entry file, loaded-on-demand references
```
toolkit/skills/coding-standards/
  SKILL.md          principles, precedence, how to pick files (short)
  structure.md      layering/separation of concerns + limits
  limits.json       numeric limits, machine-readable
  tools.md          tool -> rule-id mapping, install hints, fallback
  languages/
    python.md typescript.md sql.md html.md nginx.md docker.md powershell.md
```
- *Why:* progressive disclosure keeps context small, and adding a language is adding a file. `limits.json` keeps numbers out of prose so a script can read them.
- *Alternative:* one large SKILL.md (what exists; always loads every language).

### D2. Rule record format
Each rule is a short block:
```
### CS-PY-007  Mutable default argument
Severity: Medium   Enforced by: ruff B006   Fallback: judgment
Bad:  def f(x=[]): ...
Good: def f(x=None): x = [] if x is None else x
```
IDs are `CS-<AREA>-<NNN>` with areas `PY`, `TS`, `SQL`, `HTML`, `NGX`, `DOC`, `PS`, `STR`. IDs are append-only; retired rules stay in the file marked `RETIRED`.
- *Why:* stable IDs let the audit cite a rule and let a rule's text change without breaking old reports.

### D3. Enforcement is data, with graceful degradation
`tools.md` maps tool rule identifiers to standards IDs (for example Ruff `B006` to `CS-PY-007`). The audit engine can read it to attach rule IDs to scanner findings. A rule whose tool is missing still applies as judgment and is reported "not machine-checked", never silently dropped.
- Tools in scope: Ruff and mypy; ESLint and tsc; PSScriptAnalyzer; hadolint; `docker compose config -q`; sqlfluff. nginx and HTML have no deterministic check and are judgment rules. `gixy` and `nginx -t` are not used (a templated config makes both fragile).
- sqlfluff will usually be skipped in this repo (no `.sql` files); the rules still apply to SQL in other repos and, as judgment, to SQL strings in code.

### D4. Security hardening lives with each language, tagged by enforcer
SQL (parameterized queries, least privilege), PowerShell (strict mode, no `Invoke-Expression` on input, no plaintext secrets), Docker (non-root user, pinned image tags, no `latest`), nginx (TLS settings, security headers, hidden version, request limits). These overlap the audit's scanners, so each is tagged: a rule semgrep or hadolint already catches names that tool; the rest are judgment for `sec-checker`.
- *Why:* one source of truth for what "hardened" means, without duplicating scanners.

### D5. Structure: principles plus measurable limits
`structure.md` states layering and separation-of-concerns principles as judgment rules. `limits.json` holds defaults (file length, function length, nesting depth, no import cycles) the audit engine can check deterministically. Limits are defaults a repo can override by its own standards.
- *Why:* gives the deterministic checks the audit lacks, while keeping design judgment with `arch-checker`.

### D6. Precedence and migration of the existing text
Order: repo's own standards, then language file, then principles in `SKILL.md`. The repo's `wiki/Coding-Standards.md` stays as the repo override and is not duplicated; the toolkit skill references the idea of a repo override but not that path. TypeScript and React rules are kept only where framework-neutral; Next.js, Supabase and "markets" examples are dropped.

### D7. Installation and the existing global skill
The skill installs through the existing installer. Because the user already has a different `coding-standards` globally, the installer reports `differs` and leaves it. The README notes that `-Force` replaces it. No automatic replacement.

## Risks / Trade-offs

- [Rule sprawl: hundreds of rules nobody maintains] → Keep each language to rules that matter or that a tool enforces; every rule needs an example; review rule count per file in the task list.
- [Rules disagree with a tool's default config] → `tools.md` records the rule identifier, and a repo's own tool config wins under the precedence rule.
- [Judgment rules make audits non-deterministic] → They are tagged, and the audit reports them separately from machine-checked ones.
- [ID churn breaks old reports] → Append-only IDs, retired rules kept.
- [Tool names and rule identifiers drift across versions] → Pin the identifiers checked in `tools.md` with a note of the tested version, and treat an unknown identifier as unmapped, not an error.
- [Dependency on `add-code-audit-toolkit` not yet archived] → The audit-side delta is a dated follow-up task rather than a delta that would fail validation now.

## Migration Plan

1. Write the skill and verify it standalone.
2. After `add-code-audit-toolkit` is archived, add the `code-audit` delta (new tools, rule-ID citation) and teach the engine to read `tools.md` and `limits.json`.
3. Optionally replace the global skill with `-Force`; roll back by reinstalling the old copy from backup.

## Open Questions

- Default numeric limits (for example function length 50 lines) can be tuned after the first audits without changing the spec.
