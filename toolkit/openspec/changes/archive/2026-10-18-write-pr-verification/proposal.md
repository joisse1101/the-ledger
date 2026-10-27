## Why

The `write-pr` skill's testing section only lists test files and copies manual steps from an OpenSpec
`tasks.md`. A reviewer gets no record of what the author actually ran and saw, and no guidance on how to
review the PR. In `tasks.md` the verification is buried in task text: some tasks record an observed
result (`result: three files copied, up to date at 1.0.0`), many only say "verify X" with a checked box,
and a branch may have no `tasks.md` at all. The skill needs to separate what is known from what is
guessed, and ask the author instead of inventing results.

## What Changes

- Add an **Author Verification** subsection to the template's testing section: one bullet per check,
  with the command or input and the observed result.
- The skill drafts those bullets from the matching OpenSpec `tasks.md`. A task with a recorded result
  yields a bullet with that result. A checked "verify X" task with no result yields a bullet with no
  result invented, and the skill flags it. A task that is plain work, not verification, is skipped.
- Where `tasks.md` is missing, empty of verification, or has bare verifies, the skill asks the user once,
  batched across all groups, what they ran and saw, before presenting.
- Add a **How to Test This PR** subsection: reviewer steps the skill suggests from the group's commits
  and diff, its `tasks.md`, and the repo's own docs. Steps are limited to:
  - a checkout step;
  - run steps that use a command a document states (`tasks.md`, `CLAUDE.md`, README, package scripts)
    and that the diff points to, with every path in the command checked to exist in the checkout;
  - read steps ("start at X, it holds the change").
  The skill never invents a command or flag that no document mentions.
- In the present step, tag each bullet and step with its source (`tasks.md N.N, result recorded`,
  `tasks.md N.N, no result recorded`, `repo docs`, `inferred from diff`) so the user can judge how far
  to trust it. The tags are removed from the PR body.
- Derive the Automated and Manual checkboxes from the Author Verification bullets: Manual is ticked
  only when at least one bullet is a manual check. The template carries no hard-coded counts; a count
  appears only when `tasks.md` records one.
- Bump the skill version and `last_updated`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `toolkit-skills`: the requirement "PR content follows the template" changes. The testing section gains
  Author Verification and reviewer steps, the manual-testing box is derived from the verification
  bullets, and a new requirement covers the ask-once behavior and the grounding rules.

## Impact

- Updated: `toolkit/skills/write-pr/pr-template.md` (new subsections and ticking rules) and
  `toolkit/skills/write-pr/SKILL.md` (compose and present steps, version).
- Updated: `toolkit/README.md` and the matching `wiki/` page where they describe the PR body.
- Updated: `openspec/specs/toolkit-skills/spec.md` (at archive, from the delta).
- `python check_docs.py` must pass: version block, size budgets, links.
- No change to the installer or to the merge guard.
- Not included: running the suggested reviewer steps, and checking recorded results against reality.
  The author is responsible for reviewing the draft before confirming.
