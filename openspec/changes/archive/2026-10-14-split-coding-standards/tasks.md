## 1. Confirm rule behavior

- [x] 1.1 In a scratch project, create `.claude/rules/` with one unscoped and one `paths:`-scoped rule, and record whether each loads on reading an existing matching file and on creating a new one; note the Claude Code version and the result in `design.md` Risks

## 2. Installer support for rules

- [x] 2.1 Add a `rules` entry (`~/.claude/rules`, `.claude/rules`) to `toolkit/install/targets.json` and verify the JSON parses
- [x] 2.2 Add `-Rule`, the available-rules list (`.md` files in `toolkit/rules/`), the unknown-name error and the rule items to `Install-Toolkit.ps1`, and verify `-List` shows rules and an unknown `-Rule` name fails naming the available rules
- [x] 2.3 Verify global and `-Scope project` install, `differs` without `-Force`, `up to date`, `-Force` overwrite, and `-Uninstall` that leaves a foreign rule untouched, using a temporary project folder
- [x] 2.4 Update `toolkit/README.md` with the rules item type, the `-Rule` option, the manual install row and the result of 1.1

## 3. Write the rules

- [x] 3.1 Create `toolkit/rules/core-principles.md` (no `paths:`, <= 2 KB) covering every principle in the `toolkit-coding-standards` core requirement as must/never lines, and verify its size and that it holds no style preference
- [x] 3.2 Create `toolkit/rules/architecture-boundaries.md` (no `paths:`, <= 2 KB) covering workspace boundaries, data-layer isolation, shared contracts, server-side authorization and config schema validation, and verify the combined unscoped size is <= 4 KB
- [x] 3.3 Create `toolkit/rules/typescript-react.md` from the existing TypeScript and React sections, scoped to ts, tsx, js, jsx, css and html, with the single-API-client rule in the rules part and design tokens, colocated styles, single-source breakpoints and size-independent views under a final "Prefer" heading, and verify <= 3 KB with no content left behind in the skill
- [x] 3.4 Create `toolkit/rules/java.md` scoped to `java` (<= 3 KB) and verify it only adds Java mechanics on top of the core rule
- [x] 3.5 Create `toolkit/rules/python.md` scoped to `py` (<= 3 KB) with the same check
- [x] 3.6 Create `toolkit/rules/config-files.md` scoped to yml, yaml, json and toml (<= 3 KB) and verify it covers schema validation, no secrets and additive changes
- [x] 3.7 Create `toolkit/rules/scripts.md` scoped to ps1, sh and bat (<= 3 KB) and verify it covers fail-fast flags and idempotent re-runs

## 4. Slim the review skill

- [x] 4.1 Rewrite `toolkit/skills/coding-standards/SKILL.md` as a <= 4 KB review checklist (code smells, naming, testing structure, comments, and language-agnostic style such as matching surrounding code, clear names and short functions) with a narrow review-focused description, and verify it holds no content owned by a rule
- [x] 4.2 Remove every reference to `frontend-patterns`, `backend-patterns`, `api-design` and `rules/common/coding-style.md`, and verify with a search that none remain

## 5. Slim the project's own rules

- [x] 5.1 Rewrite the "Local rules" of `api/CLAUDE.md` to project facts only (`isolated_db`, `claude_*.py` path, `is_local` on delete routes, no `CORSMiddleware`, the `Open-ClaudeRepoWindow.ps1` path, `check_docs.py`), add a one-line pointer to the toolkit rules, and verify none of the general principles from the new rules is restated
- [x] 5.2 Do the same for `web/CLAUDE.md` (`npm run build`, `tokens.css`, `breakpoints.ts`, `types.ts`, `apiFetch`, no E2E harness), and verify nothing project-specific was lost against the original
- [x] 5.3 Verify both files are not larger than before, stay under the 4 KB nested budget, and that `cd api; python check_docs.py` passes

## 6. Check and document

- [x] 6.1 Add the toolkit checks (unscoped rules and budgets, `paths:` present and non-overlapping, skill size, references resolve) to `api/check_docs.py` with tests, and verify `cd api; python check_docs.py` and `pytest` pass
- [x] 6.2 Verify the whole flow: `Install-Toolkit.ps1 -List` reports the existing `coding-standards` skill as `differs`, and a project-scope install into a scratch folder produces the skill and all seven rules
- [x] 6.3 Run `openspec validate split-coding-standards --strict` and confirm it passes
