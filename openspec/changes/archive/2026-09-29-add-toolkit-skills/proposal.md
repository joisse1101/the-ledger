## Why

Custom AI-agent skills currently live loose in `~/.claude/skills/` on one PC: no version history, no
single place to audit or update them, and no repeatable way to get them onto a new machine, a
junior engineer's machine, or a new project. The workflow should not depend on any one vendor's
plugin marketplace; a reader who knows where a tool wants its skills should be able to do it by hand,
with a script only automating that same deterministic workflow.

## What Changes

- Add a fifth top-level folder, `toolkit/`, holding only `skills/` for now (agents and the
  `hooks/` migration are deliberately deferred).
- `toolkit/skills/<name>/SKILL.md` is the tool-neutral source of truth, one folder per skill.
  A small sample skill ships with it so the install path can be seen working.
- Add `toolkit/install/Install-Skills.ps1`: copies skills from the toolkit into Claude Code's
  skill folders, either globally (`~/.claude/skills/`) or into a given project
  (`<project>/.claude/skills/`). Supports installing one named skill or all, listing status
  (`-List`), and uninstalling toolkit-owned skills. The per-tool destination lives in a data file
  (`toolkit/install/targets.json`) so another tool later is a new row, not new code. Claude Code is
  the only target in v1.
- Add `toolkit/README.md`: a quick start (download/clone and install everything) and a separate
  Skills section documenting the manual path (which folder to copy where) before the script.
- Update `CLAUDE.md`'s "exactly four top-level folders" wording to five and describe `toolkit/`.
- Existing skills in `~/.claude/skills/` are left untouched; nothing is migrated in this change.

## Capabilities

### New Capabilities
- `toolkit-skills`: the layout of `toolkit/skills/`, and how the installer copies, lists and removes
  skills for a global or project scope without overwriting a drifted copy silently.

### Modified Capabilities

(none)

## Impact

- New files only under `toolkit/`, plus a doc edit in `CLAUDE.md`. No change to `api/`, `web/`,
  `gateway/` or `hooks/`, and none to their tests or specs.
- Consumers get the toolkit by cloning this repo or downloading just the `toolkit/` folder;
  nothing else in the repo is needed to use it.
- The installer writes only into the chosen skills folder; it never edits `settings.json` or hooks.
