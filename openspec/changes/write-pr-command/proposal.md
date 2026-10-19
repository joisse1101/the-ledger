## Why

`write-pr` is a manual-only skill, so it is typed as `/write-pr`, outside the `jois:` family that holds
the other personal workflow command (`/jois:stage`). Its three support documents are always read on
every run, so the skill form's benefit (loading support files on demand, auto-discovery) does not apply
to it. Separately, its Author Verification section is drafted only from `tasks.md` and the user's reply,
although the session it runs in often already shows the tests the author ran and their results.

## What Changes

- Replace the skill `toolkit/skills/write-pr/` with one command file `toolkit/commands/jois/write-pr.md`,
  run as `/jois:write-pr`. The steps, the confirmation word, the guidelines, the PR template and the
  verification rules move into that file. The skill folder is deleted. **BREAKING**: `/write-pr` stops
  existing; an installed copy at `~/.claude/skills/write-pr` must be removed by hand.
- Keep the `PreToolUse` hook that blocks `gh pr merge`, `--auto` and merge calls through `gh api`, now in
  the command's frontmatter.
- Add the conversation as a source of Author Verification. When the command runs in a chat that shows
  test, build or lint commands being run, it drafts a bullet for each run that covers a group, with the
  outcome visible in the output, tagged `chat` when presented. A run is not used for a group when it
  does not cover the group's changed directories or when a later edit in the chat touched a file in
  the group's diff; a stale or failed run is reported to the author instead.
- Chat evidence counts as recorded verification: a group it covers is not part of the one question to the
  user. With no usable chat (fresh session, compacted history), the existing `tasks.md` and ask-the-user
  path applies unchanged.
- Offer to run missing tests. For a group with no usable verification whose diff changes a directory
  with a documented test command, the command asks once, for all such groups, whether to run those
  commands, waits, and runs only what the user agrees to. The run lands in the chat and becomes a
  `chat` bullet. A failing or timed-out run is reported, never fixed, and does not block the PR. A
  declined offer, or no documented command, falls back to asking what the user ran.
- Update the toolkit README, the Repository Layout wiki page, the version and the docs check inputs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-skills`: the "Manual-only PR skill" requirement becomes a manual-only command under
  `toolkit/commands/jois/`; "Author verification is recorded, not invented" gains the chat source;
  "Reviewer steps are grounded and sourced" gains the `chat` tag; "The skill never merges" names the
  command as the hook's owner, and a new requirement covers offering to run missing tests.

## Impact

- `toolkit/commands/jois/write-pr.md` (new), `toolkit/skills/write-pr/` (deleted).
- `toolkit/README.md` (the `write-pr` section moves under Commands), `wiki/Repository-Layout.md`.
- `api/check_docs.py` needs no edit: the `jois/*.md` glob already checks the new file's version and
  hidden flag, and the removed skill drops out of the `skills/*/SKILL.md` glob.
- Installed copies: `Install-Toolkit.ps1` only manages items that exist in the toolkit, so the old
  `~/.claude/skills/write-pr` is left behind; the README gets a one-line removal note. The installed
  `~/.claude/commands/jois` folder differs from the toolkit's, so installing it needs `-Force`.
