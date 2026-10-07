## 1. Skeleton and rule format

- [ ] 1.1 Create `toolkit/skills/coding-standards/` with a short `SKILL.md` (principles, precedence order, which file to load for which code) and verify it is under 4 KB and links only to files in the folder
- [ ] 1.2 Define the rule block format and area codes in `SKILL.md`, and verify one sample rule parses with a small script that extracts ID, severity, enforced-by, fallback and examples
- [ ] 1.3 Add `limits.json` and `structure.md` (principles as judgment rules, numeric limits for file length, function length, nesting depth, no import cycles) and verify `limits.json` is valid JSON with every limit referenced by a `CS-STR-` rule

## 2. Language references

- [ ] 2.1 Write `languages/python.md` (style plus hardening, mapped to Ruff and mypy rules) and verify every rule has an ID, severity, enforced-by and example
- [ ] 2.2 Write `languages/typescript.md` covering TypeScript and framework-neutral React rules only (mapped to ESLint and tsc), dropping the Next.js, Supabase and "markets" examples, and verify no framework-specific example remains
- [ ] 2.3 Write `languages/powershell.md` (strict mode, no `Invoke-Expression` on input, no plaintext secrets; PSScriptAnalyzer rules) and verify the rules apply to `Start-Ledger.ps1` and `toolkit/install/Install-Skills.ps1` by spot check
- [ ] 2.4 Write `languages/docker.md` for Dockerfile and docker-compose (non-root, pinned tags, healthchecks; hadolint rules and `docker compose config -q`) and verify against `gateway/Dockerfile` and `gateway/docker-compose.yml` by spot check
- [ ] 2.5 Write `languages/sql.md` (parameterized queries, naming, least privilege; sqlfluff rules; applies to SQL strings in code as judgment) and verify it contains at least one hardening rule
- [ ] 2.6 Write `languages/nginx.md` (TLS, security headers, hidden version, request limits, templating conventions; all judgment) and verify against `gateway/nginx.conf.template` by spot check
- [ ] 2.7 Write `languages/html.md` (semantics, accessibility basics, no inline scripts; judgment) and verify it contains no rule that depends on a framework

## 3. Tool mapping

- [ ] 3.1 Write `tools.md` mapping each tool rule identifier to a standards ID, with install hints, tested versions and the judgment fallback, and verify every non-judgment rule in the language files appears in it
- [ ] 3.2 Add a check script (stdlib Python) that validates ID uniqueness, required fields, `tools.md` and `limits.json` consistency, and unresolved references, and verify it passes on the skill and fails on a seeded duplicate ID

## 4. Repo integration

- [ ] 4.1 Confirm the precedence rule against `wiki/Coding-Standards.md` and verify the skill does not duplicate that page's content
- [ ] 4.2 Run the installer against a temp project path and verify `coding-standards` installs, and that against the existing global copy it reports `differs` without overwriting
- [ ] 4.3 Update `toolkit/README.md`, `CLAUDE.md` and `wiki/Repository-Layout.md` for the new skill and the `-Force` note, and verify `cd api; python check_docs.py` passes

## 5. Audit follow-up (after `add-code-audit-toolkit` is archived)

- [ ] 5.1 Add a `code-audit` delta: PSScriptAnalyzer, hadolint, `docker compose config -q` and sqlfluff as optional tools, and findings citing a standards rule ID when one applies; verify `openspec validate --strict` passes
- [ ] 5.2 Teach `audit.py` to read `tools.md` and `limits.json` to attach rule IDs and check structure limits, and verify with fixture findings
- [ ] 5.3 Run `openspec validate expand-coding-standards --strict` and verify it reports the change valid
