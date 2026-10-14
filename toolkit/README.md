# Toolkit

Reusable AI-agent skills, slash commands and rules, kept in one place so they have version history and can
be put on any machine or project. Nothing here depends on a vendor's plugin marketplace: a skill or
command or rule is just files, and the script below only automates copying them.

Claude Code is the only supported tool today.

## Quick start

1. Get the toolkit: clone this repo, or download just the `toolkit/` folder.
2. Install everything globally (Windows PowerShell):

   ```powershell
   cd toolkit\install
   .\Install-Toolkit.ps1
   ```

3. Start a new Claude Code session; the skills, commands and rules are now available.

Other things the script does:

```powershell
.\Install-Toolkit.ps1 -List                                   # what's installed, and has it drifted?
.\Install-Toolkit.ps1 -Skill coding-standards                 # just one skill
.\Install-Toolkit.ps1 -Command opsx                           # just one command item
.\Install-Toolkit.ps1 -Rule java.md                           # just one rule
.\Install-Toolkit.ps1 -Scope project -Path C:\code\my-app     # into a project instead of globally
.\Install-Toolkit.ps1 -Force                                  # overwrite a copy that differs
.\Install-Toolkit.ps1 -Uninstall                              # remove toolkit items (only those)
```

Passing `-Skill`, `-Command` and/or `-Rule` limits the run to those items. An item already installed that
differs from the toolkit's copy is never overwritten unless you pass `-Force`; `-List` shows it as
`differs`. The script writes only inside the skills, commands and rules folders — it never touches
`settings.json` or hooks.

## Skills

Each skill is a folder `toolkit/skills/<name>/` with a `SKILL.md` (`name` and `description`
frontmatter, then instructions) and any support files it needs. A folder is self-contained.

## Commands

Each entry directly under `toolkit/commands/` is one command item: a `.md` file (becomes `/name`) or
a folder used as a namespace (`commands/opsx/apply.md` becomes `/opsx:apply`). The installer treats
each such entry as a unit, so `-Command opsx` installs the whole `opsx` set.

## Rules

Each `.md` file directly under `toolkit/rules/` is one rule: a short instruction file Claude Code
loads on its own, with no one needing to invoke it. A rule with no `paths:` frontmatter loads at
session start, in every project. A rule with `paths:` frontmatter (a list of globs such as
`"**/*.java"`) loads once a matching file is read or created. Tested on Claude Code 2.1.299: a
scoped rule is not present before any matching file is touched, so a change planned before any
file is opened has no rules yet. Every rule here is scoped, so sessions that never touch code
(tickets, workflows) load none of them.

The standards are split this way: two small core rules (principles and architecture
boundaries, scoped to source-code file types), one path-scoped rule per technology (TypeScript/React,
Java, Python, config files, scripts), and the `coding-standards` skill as an on-demand review
checklist. Use `-Scope project` to keep the rules out of unrelated projects. A project's own `CLAUDE.md` takes precedence.

## Installing by hand

Copy into the folder your tool reads from:

| Tool | Scope | Skills | Commands | Rules |
|---|---|---|---|---|
| Claude Code | Global | `~/.claude/skills/<name>/` | `~/.claude/commands/<entry>` | `~/.claude/rules/<name>.md` |
| Claude Code | Per project | `<project>/.claude/skills/<name>/` | `<project>/.claude/commands/<entry>` | `<project>/.claude/rules/<name>.md` |

For example, on Windows: copy `toolkit\skills\coding-standards` to
`%USERPROFILE%\.claude\skills\coding-standards`. On macOS/Linux: `cp -r toolkit/commands/opsx
~/.claude/commands/`.

Where each tool reads these from is data in `install/targets.json`, so supporting another tool is a
new entry there.
