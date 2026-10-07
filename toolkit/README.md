# Toolkit

Reusable AI-agent skills, agents and slash commands, kept in one place so they have version history
and can be put on any machine or project. Nothing here depends on a vendor's plugin marketplace: each
item is a file or folder, and the script below only automates copying it.

Claude Code is the only supported tool today.

## Quick start

1. Get the toolkit: clone this repo, or download just the `toolkit/` folder.
2. Run the installer (Windows PowerShell) and answer its menus:

   ```powershell
   cd toolkit\install
   .\Install-Skills.ps1
   ```

   It asks what to do (install, check, uninstall), where (globally or into one project), which items,
   whether to overwrite any that differ, and finally whether to set up the optional scanners. The
   scanner step is its own menu (`Install-Scanners.ps1`): tools are grouped by language, and if you run
   it inside a git repo it shows how many files of each language the repo has, so you only install
   what you use.

3. Start a new Claude Code session. Run `/code-audit` inside any git repository.

For scripting, the same installer takes flags instead of menus:

```powershell
.\Install-Skills.ps1 -List                                    # what's installed, and has it drifted?
.\Install-Skills.ps1 -Kind commands -Name code-audit          # just one item
.\Install-Skills.ps1 -Scope project -Path C:\code\my-app      # into a project instead of globally
.\Install-Skills.ps1 -Force                                   # overwrite a copy that differs
.\Install-Skills.ps1 -Uninstall                               # remove toolkit items (only those)
```

`-Kind` is `skills`, `agents` or `commands`; `-Name` picks one item of that kind. An installed copy that
differs from the toolkit's is never overwritten unless you pass `-Force`; `-List` shows it as `differs`.
The script writes only inside `skills/`, `agents/` and `commands/` — it never touches `settings.json`
or permissions.

## What is in it

| Kind | Source | Contents |
|---|---|---|
| skills | `toolkit/skills/<name>/` (a folder with `SKILL.md`) | `code-audit`: the audit engine and its reference docs |
| agents | `toolkit/agents/<name>.md` | `sec-checker`, `arch-checker`: read-only reviewers |
| commands | `toolkit/commands/<name>.md` | `code-audit`: the `/code-audit` slash command |

`/code-audit` needs all three. It installs fine globally: it still reads and writes **only the
repository it is launched in** (evidence goes to that repo's `code-audit/` folder, which is
self-ignored by git). It never accepts a path to another repo and never asks for extra directory
access. To audit a branch in isolation, start Claude in a worktree yourself: `claude -w <name>`.

## Manual install

Copy the item into the folder Claude Code reads. Per kind:

| Kind | Global (all projects) | Per project |
|---|---|---|
| skills | `~/.claude/skills/<name>/` | `<project>/.claude/skills/<name>/` |
| agents | `~/.claude/agents/<name>.md` | `<project>/.claude/agents/<name>.md` |
| commands | `~/.claude/commands/<name>.md` | `<project>/.claude/commands/<name>.md` |

On macOS/Linux, for example: `cp -r toolkit/skills/code-audit ~/.claude/skills/`,
`cp toolkit/agents/*.md ~/.claude/agents/`, `cp toolkit/commands/code-audit.md ~/.claude/commands/`.
On Windows, use `%USERPROFILE%\.claude\...` with Explorer or `Copy-Item -Recurse`.

## Optional scanners for `/code-audit`

The audit uses whichever of these are on your `PATH`. A missing tool is reported as **skipped** in the
report (never as clean), so install the ones you want covered. `Install-Scanners.ps1` (or the last step of the installer) walks you through them.

| Tool | Covers | Install |
|---|---|---|
| gitleaks | committed secrets | `winget install gitleaks.gitleaks` / `brew install gitleaks` |
| semgrep | SAST rules | `pipx install semgrep` |
| jscpd | duplicate code | `npm i -g jscpd` |
| trivy | dependency and config vulnerabilities | `winget install AquaSecurity.Trivy` / `brew install trivy` |
| ruff, eslint, tsc, mypy | Phase 0 lint and type gate, per language found in the repo | `pipx install ruff`, `npm i -g eslint typescript`, `pipx install mypy` |

Python 3 is required for the engine. Everything else is optional.

Where each tool reads items from is data in `install/targets.json`, so supporting another tool is a
new entry there.
