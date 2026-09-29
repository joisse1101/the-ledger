# Toolkit

Reusable AI-agent skills, kept in one place so they have version history and can be put on any
machine or project. Nothing here depends on a vendor's plugin marketplace: a skill is just a folder,
and the script below only automates copying it.

Today the toolkit holds skills only, and Claude Code is the only supported tool.

## Quick start

1. Get the toolkit: clone this repo, or download just the `toolkit/` folder.
2. Install every skill globally (Windows PowerShell):

   ```powershell
   cd toolkit\install
   .\Install-Skills.ps1
   ```

3. Start a new Claude Code session; the skills are now available.

Other things the script does:

```powershell
.\Install-Skills.ps1 -List                                   # what's installed, and has it drifted?
.\Install-Skills.ps1 -Skill toolkit-hello                    # just one skill
.\Install-Skills.ps1 -Scope project -Path C:\code\my-app     # into a project instead of globally
.\Install-Skills.ps1 -Force                                  # overwrite a copy that differs
.\Install-Skills.ps1 -Uninstall                              # remove toolkit skills (only those)
```

A skill already installed that differs from the toolkit's copy is never overwritten unless you pass
`-Force`; `-List` shows it as `differs`. The script writes only inside the skills folder — it never
touches `settings.json` or hooks.

## Skills

Each skill is a folder `toolkit/skills/<name>/` with a `SKILL.md` (`name` and `description`
frontmatter, then instructions) and any support files it needs. A folder is self-contained, so you
can install by hand without the script: copy it into the folder your tool reads skills from.

| Tool | Global (all projects) | Per project |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/` | `<project>/.claude/skills/<name>/` |

For example, on Windows: copy `toolkit\skills\toolkit-hello` to
`%USERPROFILE%\.claude\skills\toolkit-hello`. On macOS/Linux: `cp -r toolkit/skills/toolkit-hello
~/.claude/skills/`.

`toolkit-hello` is a sample that confirms the install worked; delete it once real skills exist.
Where each tool reads skills from is data in `install/targets.json`, so supporting another tool is a
new entry there.
