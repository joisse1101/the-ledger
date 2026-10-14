# Toolkit

Reusable AI-agent skills and slash commands, kept in one place so they have version history and can
be put on any machine or project. Nothing here depends on a vendor's plugin marketplace: a skill or
command is just files, and the script below only automates copying them.

Claude Code is the only supported tool today.

## Quick start

1. Get the toolkit: clone this repo, or download just the `toolkit/` folder.
2. Install everything globally (Windows PowerShell):

   ```powershell
   cd toolkit\install
   .\Install-Toolkit.ps1
   ```

3. Start a new Claude Code session; the skills and commands are now available.

Other things the script does:

```powershell
.\Install-Toolkit.ps1 -List                                   # what's installed, and has it drifted?
.\Install-Toolkit.ps1 -Skill coding-standards                 # just one skill
.\Install-Toolkit.ps1 -Command opsx                           # just one command item
.\Install-Toolkit.ps1 -Scope project -Path C:\code\my-app     # into a project instead of globally
.\Install-Toolkit.ps1 -Force                                  # overwrite a copy that differs
.\Install-Toolkit.ps1 -Uninstall                              # remove toolkit items (only those)
```

Passing `-Skill` and/or `-Command` limits the run to those items. An item already installed that
differs from the toolkit's copy is never overwritten unless you pass `-Force`; `-List` shows it as
`differs`. The script writes only inside the skills and commands folders — it never touches
`settings.json` or hooks.

## Skills

Each skill is a folder `toolkit/skills/<name>/` with a `SKILL.md` (`name` and `description`
frontmatter, then instructions) and any support files it needs. A folder is self-contained.

## Commands

Each entry directly under `toolkit/commands/` is one command item: a `.md` file (becomes `/name`) or
a folder used as a namespace (`commands/opsx/apply.md` becomes `/opsx:apply`). The installer treats
each such entry as a unit, so `-Command opsx` installs the whole `opsx` set.

## Installing by hand

Copy into the folder your tool reads from:

| Tool | Scope | Skills | Commands |
|---|---|---|---|
| Claude Code | Global | `~/.claude/skills/<name>/` | `~/.claude/commands/<entry>` |
| Claude Code | Per project | `<project>/.claude/skills/<name>/` | `<project>/.claude/commands/<entry>` |

For example, on Windows: copy `toolkit\skills\coding-standards` to
`%USERPROFILE%\.claude\skills\coding-standards`. On macOS/Linux: `cp -r toolkit/commands/opsx
~/.claude/commands/`.

Where each tool reads these from is data in `install/targets.json`, so supporting another tool is a
new entry there.
