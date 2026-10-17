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
.\Install-Toolkit.ps1 -List                                   # what's installed, has it drifted, which versions?
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

### The `write-pr` skill

`/write-pr` opens GitHub pull requests for the commits on the current branch. It declares
`disable-model-invocation: true`, so it runs only when you type it and stays out of the session
context. It reads the commits since the default branch, proposes groups of commits that each form one
concern (a refactor never shares a PR with a feature), and waits for a confirmation word before it
pushes or runs `gh pr create`. Each body follows `pr-template.md`: the test files the group adds, and
any manual steps recorded in the OpenSpec change's `tasks.md`. It blocks a group whose diff holds a
secret, an `.env` file or build output, and warns on debug prints.

It never merges. A hook in the skill's frontmatter blocks `gh pr merge`, `--auto` and merge calls
through `gh api`, and stays active for the rest of the session once the skill has been invoked. When
it finishes it lists every PR it opened in the order to merge, with the `gh pr merge <n> -s -d`
command for each, for you to run. A PR based on another PR's branch needs a rebase after the earlier
one merges, and the list says so. `guidelines.md` and `pr-template.md` sit beside `SKILL.md`.

## Commands

Each entry directly under `toolkit/commands/` is one command item: a `.md` file (becomes `/name`) or
a folder used as a namespace (`commands/opsx/apply.md` becomes `/opsx:apply`). The installer treats
each such entry as a unit, so `-Command opsx` installs the whole `opsx` set.

### The `jois` commands

- `/jois:stage` clears a messy working tree, with or without an OpenSpec change. It stages one
  concern at a time, shows the message and a confirmation word, and waits. Typing the word commits
  that concern and moves on, until the tree is clean. Secret files and build output are skipped and
  named. It has no commit authority of its own.

### Commands stay out of the session context

Every command declares `disable-model-invocation: true`, so its description is not loaded into each
new session's skill listing (about 300 tokens for a typical set) while you can still type
`/jois:stage`. `python check_docs.py` fails on a command without the flag. Skills such as
`coding-standards` stay discoverable on purpose. `openspec update` does not touch the installed
commands; it writes copies into the project's `.claude/commands/opsx` and `.claude/skills/openspec-*`,
which carry no flag. In a project where you do not want them listed, delete the project's
`.claude/commands/opsx` (the global install serves) or re-add the flag.

## Rules

Each `.md` file directly under `toolkit/rules/` is one rule: a short instruction file Claude Code
loads on its own, with no one needing to invoke it. A rule with no `paths:` frontmatter loads at
session start, in every project. A rule with `paths:` frontmatter (a list of globs such as
`"**/*.java"`) loads once a matching file is read or created. Tested on Claude Code 2.1.299: a
scoped rule is not present before any matching file is touched, so a change planned before any
file is opened has no rules yet. Every coding rule here is scoped, so sessions that never touch
code (tickets, workflows) load none of them. The one exception is `commit-hygiene`, which is
unscoped on purpose: commits of images, deletions, renames and docs touch no code file, so a
scoped rule would be missing exactly when those commits grow. It is capped at 2 KB and asks
nothing unless Claude is about to commit.

The standards are split this way: two small core rules (principles and architecture
boundaries, scoped to source-code file types), one path-scoped rule per technology (TypeScript/React,
Java, Python, config files, scripts), and the `coding-standards` skill as an on-demand review
checklist. The unscoped `commit-hygiene` rule keeps commits to one concern and requires the user's
confirmation word before Claude commits. Use `-Scope project` to keep the rules out of unrelated projects. A project's own `CLAUDE.md` takes precedence.

## Versions

Every skill, rule and `jois` or `jois-review` command declares its version in a `metadata:` map in its
frontmatter, as the Agent Skills format keeps it. Both keys are strings and are bumped by hand
whenever the item's guidance changes: `version` is semver (`MAJOR.MINOR.PATCH`) and `last_updated`
is the date of the change.

```yaml
---
name: coding-standards
description: ...
metadata:
  version: "1.0.0"
  last_updated: "2026-10-14"
---
```

A rule's frontmatter holds the same `metadata:` block next to its `paths:`; an unscoped rule such
as `commit-hygiene` has only the `metadata:` block and still loads in every session. A top-level
`version:` key is not accepted. `python check_docs.py` (run from `api/`) fails on a missing or
malformed version.

`-List` shows each item's version and date, and for an item that differs it shows both the
toolkit's and the installed version, so you can see at a glance that an installed copy is behind.
The version says what changed and when; the content hash decides whether anything changed at all,
so an edit that forgot to bump the version still shows as `differs`.

`skills/coding-standards/scripts/Get-ItemHash.ps1` is the one place the hash and the version are
computed. The installer dot-sources it, and you can run it on any skill folder, command folder or
`.md` file (it needs Windows PowerShell):

```powershell
.\toolkit\skills\coding-standards\scripts\Get-ItemHash.ps1 -ItemPath ~\.claude\rules\python.md
```

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
