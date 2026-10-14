## 1. The rule

- [x] 1.1 Create `toolkit/rules/commit-hygiene.md` (no `paths:`, <= 2 KB) covering the never-commit-unprompted gate (stage, print summary and message plus "reply with <word> to commit" using a common word different from the previous prompt's, commit only on the most recent prompt's word or an AskUserQuestion "Yes, commit", confirmation per commit), one concern per commit, the concern definition with its bulk/binary/rename exemptions, the split trigger, explicit-path staging with no `git add .`/`-A`/`commit -a`, non-interactive partial staging, no commit on a red build, docs/specs/tests in the same commit, and the lowercase `type(scope): subject` format; verify size with `wc -c`, that the frontmatter has no `paths:`, and that the text only applies "when about to commit"

## 2. Opsx commands

- [x] 2.1 Edit `toolkit/commands/opsx/apply.md` so "Pending Commits" defines ready-to-commit as one concern complete under the commit-hygiene rule, stages after each concern rather than at the end of the task list, and splits an oversized stage before presenting it; replace its "reply 'yes'" prompt with the varying confirmation word; verify the end-your-turn hard stop is otherwise unchanged and no remaining text accepts "yes"
- [x] 2.2 Edit `toolkit/commands/opsx/archive.md` step 7 to refer to the same rule while keeping its AskUserQuestion hard stop; verify the archive and sync changes remain a single concern in the proposed message

## 3. Docs check

- [x] 3.1 Edit `api/check_docs.py` so `_check_scoped_rules` skips an `UNSCOPED_RULES = ("commit-hygiene.md",)` entry and a new check fails if that rule has `paths:` frontmatter or exceeds 2 KB; add tests in `api/tests/test_check_docs.py` for the accepted, over-budget and scoped cases; verify with `cd api; pytest tests/test_check_docs.py` and `python check_docs.py`

## 4. Docs

- [x] 4.1 Edit `toolkit/README.md` to replace "Every rule here is scoped" with the commit-hygiene exception and its reason, and add the rule to the rules overview; verify with `cd api; python check_docs.py` that links and size budgets pass
- [x] 4.2 Run `openspec validate add-commit-hygiene-rule` and verify it passes
