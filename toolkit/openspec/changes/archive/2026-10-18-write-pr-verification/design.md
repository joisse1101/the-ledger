## Context

See proposal.md - Why. The `write-pr` skill composes each PR body from `pr-template.md` and presents it
for a confirmation word before anything is pushed (spec: "Confirmation before publishing"). Its Tests
step currently lists test files and copies "manual steps or results" from an OpenSpec `tasks.md`.

Observed in `tasks.md` files (the archived `write-pr-skill` change is the example): verification is
written as task text, not as a separate list. Three shapes occur: a verify task with a recorded
`(result: ...)`, a checked verify task with no result, and a plain work item. A branch can also have no
OpenSpec change. `SKILL.md` is about 4.7 KB; the skill's folder is copied whole by the installer, so a
new support file needs no installer change. `toolkit/` is independent of the dashboard, so the skill
cannot hardcode this repository's commands.

## Goals / Non-Goals

**Goals:**
- A reviewer sees what the author ran and what was observed, and how to review the PR.
- No result or command appears that no source states.
- The author can see how far to trust each line before confirming.

**Non-Goals:**
- Running any check or suggested step, or verifying that a recorded result is true.
- Editing `tasks.md`.
- Changing grouping, the scan, the confirmation word or the merge guard.

## Decisions

**Where the rules live.** A new support file `toolkit/skills/write-pr/verification.md` holds how to read
`tasks.md`, how to build reviewer steps, and the source tags. `SKILL.md` keeps one compose bullet and a
pointer, as it already does for `pr-template.md` and `guidelines.md`. The template holds only the
section structure and the ticking rules. *Alternative:* put everything in `SKILL.md` - rejected, it is
the text loaded on every run and the rules are only needed while composing.

**Classifying `tasks.md` entries.** A task is verification when its text asks to verify, dry-run or run
something and check the outcome. It has a recorded result when it carries a `(result: ...)` clause or
states the outcome in the task text. It yields a bullet with that result. A checked verification task
with no result yields a bullet that names the check and states no outcome, flagged `no result recorded`.
Unchecked tasks yield nothing, because the check did not happen. Other tasks yield nothing. The match is
by reading the task text, not a fixed pattern, because the archive uses no single phrasing.
*Alternative:* require a new `verification:` marker in `tasks.md` - rejected, it would not apply to the
existing archive and adds a convention to every change.

**Asking the user.** After composing and before presenting, the skill collects every group whose
verification is missing or lacks results and asks one plain-text question covering all of them, then ends
the turn. The user's reply is turned into bullets and nothing is added to it. The existing rule in the
present step, "end the turn and call no tool", still applies to the confirmation prompt; the question is
an earlier, separate turn. *Alternatives:* ask per group - rejected, several groups would mean several
interruptions; ask only at the present step - rejected, the question would arrive together with the
confirmation word and the answer would not be reviewed before it.

**Author Verification sets the manual box.** The Automated box keeps its rule (test files added or
changed, assumed run). Manual is ticked when at least one bullet is a manual check: a command run or a
behavior observed by hand, as opposed to running the repository's test command. This keeps the boxes
and the bullets from disagreeing. *Alternative:* leave the boxes independent - rejected, a ticked
Manual box over an empty section reads as a claim with no support.

**Reviewer steps.** Candidates come from three sources: the diff (which directories changed), `tasks.md`
(commands it names) and the repository's own documents (`CLAUDE.md`, README, `package.json` scripts,
the project's testing doc). A candidate is kept only if it is one of:
- a checkout step, `git fetch` then `git switch <branch>`;
- a run step whose command a document states and whose directory the diff changed;
- a read step naming a file in the diff and why to start there.
Before a run step is kept, each path or script in it is checked to exist in the checkout; a failing step
is dropped, not corrected. A flag is checked against the document that states the command, not guessed.
An undocumented script gets at most a read step. This is the "middle option": inference may choose among
documented commands and may order the reading, and it may not create a command.
*Alternatives:* only steps from `tasks.md` and docs - rejected, a PR with no `tasks.md` would get
nothing; any inferred step - rejected, it reproduces the wrong-path failure (an installer invoked from the
wrong directory) the grounding is meant to prevent.

**Source tags.** Each verification bullet and reviewer step carries a source while the PR is presented:
`tasks.md N.N, result recorded`, `tasks.md N.N, no result recorded`, `repo docs`, `inferred from diff`,
or `user`. The skill strips the tags when it writes the body for `gh pr create`. The user is responsible
for reviewing the draft; the tags show where to look first. *Alternative:* keep the tags in the body -
rejected, reviewers do not need them.

**No fixed numbers in the template.** The template's comments show the bullet shape only. A count such
as passing tests appears in a body only when a source records it.

## Risks / Trade-offs

- [A recorded result in `tasks.md` is stale or wrong] → the skill copies it and tags it; the author
  reviews before the confirmation word. Checking results against reality is a non-goal.
- [Misclassifying a task as verification, or missing one] → the bullet and its task number are visible in
  the present step, so the author can correct it in the same reply as the word.
- [The path check cannot catch a wrong flag] → run steps use only the command text as a document states
  it, with no added flags.
- [A repository with no testing docs yields few run steps] → read steps and the checkout step still
  appear; the author can add steps when changing the draft.
- [One batched question delays presenting] → it fires only when information is missing, and only once.
- [`verification.md` grows the folder] → the installer copies folders whole, and `check_docs.py` already
  checks support-file links and the version block.
