## Why

`toolkit/skills/coding-standards/SKILL.md` is one 12.8 KB skill that mixes universal principles,
TypeScript/React detail, API design, performance and testing. It is loaded whole whenever it fires,
costing context on unrelated work, and it has no Java, Python, config or script guidance even though
those are the stacks it is used on. It also points at skills that do not exist in the toolkit. A
description-routed skill is probabilistic, so language rules can be skipped; Claude Code's
path-scoped rules load when matching files are touched and fit file-shaped guidance better.

## What Changes

- Split the standards into layers: a small always-on core rule, an architecture-boundaries rule,
  path-scoped language and file-type rules, and a slimmed on-demand review skill.
- Add `toolkit/rules/` as a third toolkit item type (single `.md` files with optional `paths:`
  frontmatter) and teach the installer and `targets.json` to list, install and uninstall them.
- Write first drafts of the Java, Python, config (`.yml`/`.json`), and script (`.ps1`/`.sh`)
  playbooks, and fold the existing TypeScript/React content into a TypeScript/React rule.
- Reduce `coding-standards/SKILL.md` to a review checklist (code smells, naming, testing, comments)
  and remove its references to skills that are not in the toolkit.
- Cut content that duplicates linters and formatters, and content that is not a standard (generic
  performance and file-layout advice).
- Add size budgets for the rule and skill files to the docs check.
- Slim this repo's `api/CLAUDE.md` and `web/CLAUDE.md` to project-specific content only (paths,
  fixture and helper names, repo quirks), dropping the general principles the new rules now own.

## Capabilities

### New Capabilities
- `toolkit-coding-standards`: the layered structure of the standards, what each layer covers, which
  files each path-scoped rule applies to, and the size budget that keeps always-on content small.

### Modified Capabilities
- `toolkit-skills`: adds rules as an installable item type alongside skills and commands, with the
  same copy, no-silent-overwrite, list and safe-uninstall behavior.

## Impact

- New: `toolkit/rules/*.md`.
- Changed: `toolkit/skills/coding-standards/SKILL.md` (slimmed),
  `toolkit/install/Install-Toolkit.ps1` and `targets.json` (rules item type, `-Rule` parameter),
  `toolkit/README.md`, `api/check_docs.py` (a toolkit size-budget check), and the "Local rules"
  sections of `api/CLAUDE.md` and `web/CLAUDE.md`.
- Existing installs: a previously installed `coding-standards` skill shows as `differs` until the
  user passes `-Force`; nothing is overwritten silently. The installer still writes only inside the
  skills, commands and rules folders and never touches `settings.json`.
- Not changed: the root `CLAUDE.md` and `wiki/Coding-Standards.md`. The wiki page still repeats some
  general guidance; it is left for a follow-up.
- Dependency: the slimmed project files assume the toolkit rules are installed (globally or with
  `-Scope project`); a machine without them loses the general guidance for this repo.
