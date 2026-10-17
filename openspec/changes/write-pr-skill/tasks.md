## 1. Verify the merge guard

- [x] 1.1 Verify on a throwaway skill that a `PreToolUse` hook declared in a skill's frontmatter blocks a `Bash` call while the skill runs and not after; record the result and, if it never runs, switch design decision "Never merging" to a documented global `permissions.deny` snippet before continuing (result on 2.1.302: the frontmatter hook runs and blocks, but stays active for the rest of the session once the skill is invoked, not only while its steps run; `${CLAUDE_SKILL_DIR}` did not resolve in the hook command, so a script cannot be located independent of the working directory; an inline command blocked correctly, so the guard is inline with no script file)
- [x] 1.2 Add the inline `PreToolUse` guard to the `write-pr` frontmatter, which blocks `gh pr merge`, `--auto` and `gh api` merge calls, and verify by piping sample hook input (`gh pr merge 5 -s -d`, `gh pr create --auto`, `gh api .../merge`) into the same command that each exits with a block while `gh pr create` and `git push` pass

## 2. Skill content

- [x] 2.1 Add `toolkit/skills/write-pr/pr-template.md` (the agreed template without the visual-proof section, with Related Issues marked optional) and `guidelines.md` (the four rules, hard rules and best practices), and verify both resolve from `SKILL.md`
- [x] 2.2 Write `toolkit/skills/write-pr/SKILL.md` with `name`, `description`, `disable-model-invocation: true`, `allowed-tools` (no merge), the hook from 1.1, and a `metadata:` block with `version` and `last_updated`; cover the refusal on `main`, commit reading, grouping and confirmation, branches for later groups, title and body rules, the OpenSpec `tasks.md` lookup, the diff scan, the confirmation word, and the merge-order summary; verify it stays within the size budget
- [ ] 2.3 Dry-run the skill on a sample branch with two unrelated commits and verify it proposes two PRs, creates nothing before the word, and ends with an ordered merge list and `gh pr merge <n> -s -d` lines
- [ ] 2.4 Dry-run on a branch with a `.env` file and a `console.log` and verify the file blocks that PR while the print only warns
- [ ] 2.5 Attempt `gh pr merge` after invoking the skill and verify the hook blocks it

## 3. Docs and checks

- [ ] 3.1 Update `toolkit/README.md` (skills section and manual-install note) and the matching `wiki/` page for the new skill, linking pages as `[text](Page-Name.md)`
- [ ] 3.2 Extend `api/check_docs.py` and `api/tests/test_check_docs.py` if needed so the new skill folder, its version block and its support-file links are covered; run `cd api; pytest` and `python check_docs.py` and verify both pass
- [ ] 3.3 Run `Install-Toolkit.ps1 -Skill write-pr -Scope project -Path <temp>` and verify the whole folder, including its support files, is copied and `-List` shows it up to date
