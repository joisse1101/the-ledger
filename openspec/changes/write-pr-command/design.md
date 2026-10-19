## Context

See proposal.md - Why. Today `toolkit/skills/write-pr/` holds `SKILL.md` (about 80 lines, with a
`PreToolUse` hook in its frontmatter) plus `guidelines.md`, `pr-template.md` and `verification.md`. Every
run reads all three documents. `toolkit/commands/jois/stage.md` is the existing single-file command.

Constraints found in the Claude Code docs: a command file takes the same frontmatter as a skill
(including `hooks`) except `name` and `paths`; the `jois:` prefix comes only from a `commands/` subfolder
(or a plugin, which the toolkit avoids); a command or skill without `context: fork` runs inline and sees
the conversation; any extra `.md` in `commands/jois/` would become its own command.

## Goals / Non-Goals

**Goals:**
- One file, `/jois:write-pr`, with the same behavior as the skill plus the chat source.
- The chat rules are written so the model can apply them from the transcript alone, with no tool that
  re-runs anything.

**Non-Goals:**
- The command runs no check on its own initiative: it runs a documented test command only after the user
  agrees to that command in answer to its question. It never edits code to make a run pass.
- No change to grouping, the template, the confirmation word, the self-review scan or the merge-order
  summary.
- No plugin packaging, and no `/write-pr` alias.
- The Automated checkbox rule is unchanged: it still ticks on added or changed test files.

## Decisions

**Merge into one command rather than keep the skill.** The skill form earns its keep when support files
are conditional; here all three are needed every run, and the flag keeps the description out of the
listing either way. A thin command pointing at the skill cannot work: `disable-model-invocation` blocks
the Skill tool, and a path-based read breaks in project-scope installs. Keeping the skill and dropping
the prefix was rejected because the prefix is what was asked for. The merged file is about 230 lines,
under the 500-line guidance, and costs nothing until typed.

**File layout.** Frontmatter (name, description, allowed-tools, hooks, metadata) then the old `SKILL.md`
steps, then three sections, `Guidelines`, `PR body template` and `Author Verification`, holding the former
documents verbatim except for the verification changes. Section names match the old file names so the
steps can point at them ("see Author Verification below").

**Version 2.0.0.** The invocation name changes, which is breaking for anyone who types `/write-pr`.
`last_updated` is the date of the change.

**Chat evidence rules** (in the Author Verification section):
- A *run* is a test, build, type-check or lint command whose output appears in the conversation, whether
  the assistant ran it or the user ran it with `!`.
- A run covers a group when its working directory or paths include a directory the group's diff changes;
  a run at the repository root covers every group.
- Only the outcome and counts visible in the output are quoted. Nothing is inferred from the command
  alone.
- Latest run of a command wins. If it failed, the command is reported to the author as failed and yields
  no passing bullet. If an Edit or Write in the conversation touched a file in the group's diff after the
  run, the run is reported as out of date and yields no bullet. Both are shown in the present step as
  warnings, not blocks.
- Precedence is not a ranking: a chat bullet and a `tasks.md` bullet can both appear, each with its source
  tag, because they record different runs.
- A group with at least one usable bullet from any source is not in the single "ask the user" question.

**Offer to run missing tests** (runs where the "ask the user once" step sits today):
- It reuses the reviewer "Run" step rules to pick a command: a repository document states it, the diff
  changes its directory, every path in it exists, no flags are added. Nothing is invented.
- One question for all groups, then the turn ends. This extends the existing ask-once rule; a declined
  offer or an undocumented directory falls through to asking what the user ran.
- Agreed commands run through the normal permission prompt. `allowed-tools` gets no test patterns
  because test commands differ per repository; pre-allowing them would widen what the command can run
  unprompted.
- The run happens in the chat, so the chat-evidence rules above turn it into a `chat` bullet with no
  second mechanism.
- It runs on the branch tip including uncommitted changes, not on each group's cherry-picked subset.
  For several groups from one branch the result describes the whole tip; the bullet names the command
  and directory so the author sees that. Checking out each group to test it is much heavier and is not
  done.
- A failed run is reported and never fixed, gets no passing bullet and does not block the PR (the same
  treatment as a failed chat run). A run past the shell timeout counts as no result and is reported.

**Staleness by edits in the chat, not by commit time.** The command cannot know when a commit was made
relative to a run without extra git calls, and commits made outside the chat would defeat it. Edits seen
in the conversation are the reliable signal. A file changed outside the chat after the run is not
detected; the `chat` tag in the present step tells the author where the claim came from so they can
judge.

**Migration of installed copies.** The installer deliberately touches only items present in the toolkit,
so a removed skill is not uninstalled. The README states that `~/.claude/skills/write-pr` should be
deleted by hand. Keeping it would leave a working but stale `/write-pr`.

**Spec wording.** Only the requirements whose behavior changes are modified. The other `write-pr`
requirements still say "the skill"; the modified first requirement states they apply to the command.
Rewriting all nine for a noun change would be a large diff with no behavior change.

## Risks / Trade-offs

- [The merge-blocking hook may not fire from a command's frontmatter] -> The docs say hooks apply to
  commands. A manual task asks `/jois:write-pr` to run `gh pr merge` and confirms the block before the
  change is archived; if it does not fire, stop and reconsider keeping a skill.
- [The model treats a summarized conversation as full history] -> The rule says a compacted history
  contributes nothing, and the tag `chat` is shown to the author before any PR opens.
- [A run covered more than the diff, such as a root `npm test`] -> Reported as covering the group; the
  bullet quotes the command so the author sees the scope.
- [Running repository commands executes repository code] -> Only documented commands, only after the
  user agrees to the named command, and each still goes through the permission prompt.
- [A long suite stalls the turn] -> The shell timeout caps it; a timeout is reported as no result.
- [The file is long for a command] -> Under the 500-line guidance and read only on invocation.

## Migration Plan

1. Land the command and delete the skill folder in one commit pair (see tasks).
2. Run `Install-Toolkit.ps1 -Command jois -Force`, delete `~/.claude/skills/write-pr`, start a new session.
3. Rollback: revert the commit and reinstall the skill.
