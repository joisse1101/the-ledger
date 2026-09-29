## Context

Skills are folders with a `SKILL.md` (frontmatter `name`/`description` plus markdown and optional
support files). Claude Code reads them from `~/.claude/skills/` (global) and `<project>/.claude/skills/`
(project). The repo's other PowerShell tooling (`hooks/*Install*.ps1`, `Start-Ledger.ps1`) sets the
style for an installer here. The user's existing skills in `~/.claude/skills/` stay as they are.

## Goals / Non-Goals

**Goals:**
- One place in the repo for all custom skills, auditable through git.
- A one-command install to global or project scope, and a documented manual path that needs no script.
- Adding another AI tool later is adding a row of data.

**Non-Goals:**
- Agents, and moving `hooks/` into the toolkit (both deferred).
- Migrating the skills already in `~/.claude/skills/`.
- Any marketplace, plugin manifest or vendor-specific packaging.
- Non-Windows installer (README documents the manual copy, which works anywhere).

## Decisions

**Layout.** `toolkit/skills/<name>/SKILL.md`, `toolkit/install/Install-Skills.ps1`,
`toolkit/install/targets.json`, `toolkit/README.md`. A fifth top-level folder; CLAUDE.md's
"exactly four" wording is updated.

**Copy, not symlink.** Symlinks/junctions are unreliable on Windows and break if the toolkit moves.
A copy always works. Cost: updates need a re-run, which `-List` makes visible.

**Targets as data.** `targets.json` maps a target name (`claude-code`) to a global skills path and a
project-relative skills path. The script reads it; v1 has one entry.

**Drift detection by content hash.** Compare a hash over each skill folder's files (relative path +
content) between source and destination. Same: "up to date". Different: "differs", skipped unless
`-Force`. Absent: "missing", copied. This is what makes `-List` an audit view.

**Uninstall by toolkit membership.** Only names present in `toolkit/skills/` are removable, so a
person's own skills in the same folder are never touched.

**CLI surface.** `Install-Skills.ps1 [-Scope global|project] [-Path <project>] [-Skill <name>]
[-List] [-Uninstall] [-Force] [-Target claude-code]`. Default scope is global.

**Sample skill.** A trivial `toolkit-hello` skill (says the toolkit installed correctly) so the flow
can be verified end to end and deleted later.

## Risks / Trade-offs

- Cloning the whole repo to get skills pulls the dashboard too; accepted, since downloading only
  `toolkit/` is also documented.
- A copied skill can drift from the toolkit; mitigated by `-List` and the no-silent-overwrite rule.
- Skill folder paths for Claude Code could change in a future release; isolated to `targets.json`.
