## Why

Claude produces very large commits. `opsx:apply` and `opsx:archive` only gate *when* to commit
(stage, show the message, wait for approval); nothing says how big a commit may be or what may share
one. "Ready to commit" is undefined, and apply loops over every pending task, so several tasks end up
staged as one commit (for example `28e260c`: 24 files, +901 -583, mixing content, installer,
validator, specs and docs). Reviewing and reverting such commits is hard.

## What Changes

- Add an unscoped `toolkit/rules/commit-hygiene.md` that loads in every session and applies whenever
  Claude is about to commit. It sets one concern per commit, a size trigger for hand-written changes,
  explicit-path staging, no commit while the build or tests are red, and the repo's lowercase
  `type(scope): subject` message format.
- Forbid Claude from ever committing on its own. It stages, proposes a message, and commits only after
  the user types a confirmation word that Claude names in the prompt (a common word, never the same as in
  its previous prompt) or picks "Yes, commit" in an AskUserQuestion.
- Count *concerns*, not files, so a cleanup, a batch of deletions or renames, a regenerated asset or a
  lockfile is one concern however many files it touches, and is never bundled with a code change.
- Make `opsx:apply` and `opsx:archive` defer to the rule: "ready to commit" means one concern is
  done, and apply stages after each concern rather than at the end of the task list.
- Reword `toolkit/README.md`, which says every rule is scoped, to state that this rule is
  deliberately unscoped and why.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `toolkit-coding-standards`: adds the unscoped commit-hygiene rule (content, size budget, and the
  exemption from the code-scoped requirement) and the requirement that the apply and archive
  commands defer to it.

## Impact

- New: `toolkit/rules/commit-hygiene.md`.
- Changed: `toolkit/commands/opsx/apply.md`, `toolkit/commands/opsx/archive.md`, `toolkit/README.md`.
- Changed: `api/check_docs.py` and `api/tests/test_check_docs.py`. The scoped-rule check treats every
  rule outside the two core rules as a technology rule and demands `paths:`, so it fails on the new
  unscoped rule. The check gains an explicit unscoped-rule exemption that requires the rule to have no
  `paths:` and to stay within 2 KB.
- Cost: the rule sits in context in every session where the toolkit is installed. It is kept to about
  15 lines. It does nothing outside a git repo, since nothing is committed there.
- Existing installs: nothing is overwritten silently; the installer reports changed commands as
  `differs` until `-Force`.
