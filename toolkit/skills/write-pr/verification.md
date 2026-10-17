# Author Verification and reviewer steps

How to fill the two testing subsections of `pr-template.md`. Nothing here runs a check: the skill
reads sources and reports what they say.

## Author Verification

Find the OpenSpec change as in `SKILL.md`, then read its `tasks.md`. Sort each task by its text:

| Task | Bullet |
|---|---|
| Checked, asks to verify, dry-run or run something, and records the outcome (a `(result: ...)` clause or the outcome in the text) | The check and the recorded result. Source `tasks.md N.N, result recorded`. |
| Checked, asks to verify, but records no outcome | The check only, no outcome. Source `tasks.md N.N, no result recorded`. |
| Unchecked, or plain work with nothing to verify | None. |

Never add a result a source lacks. Quote a count (tests passed, files copied) only when the source
gives it. A bullet is **manual** when it is a command run or behavior seen by hand; running the
repository's test command is automated.

## Missing verification

A group needs the user's input when it has no OpenSpec change, `tasks.md` has no verification task, or a
bullet has no recorded result. Collect every such group and ask the user **once**, in plain text, what
they ran and saw, then end the turn. Do not ask per group. Turn the reply into bullets, source `user`,
and add nothing the reply did not say. If the user ran nothing, write `- None recorded.` and leave
Manual unticked.

## How to Test This PR

Suggest steps from the group's diff, its `tasks.md` and the repository's own documents (`CLAUDE.md`,
README, `package.json` scripts, a testing page). Keep a step only if it is one of:

1. **Checkout**: `git fetch`, then `git switch <branch>`. Always first.
2. **Run**: a command a document states, for a directory the diff changed, copied as written with no
   added flags. Check that every script and path in it exists in the checkout; drop the step if one does
   not. Do not repair it.
3. **Read**: a file in the diff and why to start there. A script no document explains gets a read step
   at most, never a run step.

Never invent a command or flag. Put each command in a fenced block. Delete the subsection if only the
checkout step is left and the diff has nothing worth reading first.

## Sources

When presenting a PR, tag every bullet and step: `tasks.md N.N, result recorded`,
`tasks.md N.N, no result recorded`, `repo docs`, `inferred from diff` (a read step, or a run step chosen
among documented commands) or `user`. The author reviews the draft and the tags show where to look
first. Strip every tag from the body passed to `gh pr create`.
