## 1. Move the skill into a command

- [x] 1.1 Create `toolkit/commands/jois/write-pr.md` with frontmatter (`name`, `description`, `allowed-tools`, `disable-model-invocation: true`, the merge-blocking `PreToolUse` hook, `metadata.version` "2.0.0" and today's `last_updated`) and the former `SKILL.md` steps; verify `python check_docs.py` from `api/` reports no problem for the file
- [x] 1.2 Append the contents of `guidelines.md`, `pr-template.md` and `verification.md` as the `Guidelines`, `PR body template` and `Author Verification` sections, and point the steps at them; verify no reference to a sibling file name remains with a search for `guidelines.md`, `pr-template.md` and `verification.md` in the new file
- [x] 1.3 Delete `toolkit/skills/write-pr/` and verify `toolkit/skills/` holds only `coding-standards`

## 2. Chat history as a verification source

- [x] 2.1 In the Author Verification section add the chat-run rules (what a run is, coverage by directory, quote only visible outcomes and counts, latest run wins, failed and out-of-date runs warned and not used, fresh or summarized history contributes nothing) and verify each scenario in the `toolkit-skills` delta spec has a matching sentence
- [x] 2.2 Add `chat` to the source tags in the present step and to the missing-verification rule (a group with a usable bullet from any source is not asked about), and verify the strip-tags instruction for the PR body still names every tag

- [x] 2.3 Add the offer-to-run step to the missing-verification rule: select documented commands by the reviewer Run-step rules, ask once for all groups and end the turn, run only agreed commands, report failures and timeouts without fixing them, fall back to asking what the user ran on a decline or no command; verify each scenario of the "Missing tests are offered to the user to run" requirement has a matching sentence and that `allowed-tools` gains no test-command pattern

## 3. Docs

- [x] 3.1 Move the `write-pr` section of `toolkit/README.md` from Skills to the `jois` commands list as `/jois:write-pr`, add the chat-history and offer-to-run behavior and the one-line removal note for `~/.claude/skills/write-pr`; verify `python check_docs.py` passes from `api/`
- [x] 3.2 Update the `toolkit/` sentence in `wiki/Repository-Layout.md` so `write-pr` is listed under the `jois` commands and not the skills; verify `python check_docs.py` passes

## 4. Verification

- [x] 4.1 Run `openspec validate write-pr-command --strict` and verify it passes (result: change is valid)
- [x] 4.2 Install with `toolkit/install/Install-Toolkit.ps1 -Command jois -Force`, delete `~/.claude/skills/write-pr`, start a new session, and verify `/jois:write-pr` is offered, `/write-pr` is not, and `/context` does not list the command description (result: reported working by the author after installing and starting a new session)
- [x] 4.3 In that session, after invoking `/jois:write-pr`, ask Claude to run `gh pr merge 1` and verify the hook blocks it with the "write-pr never merges" message (result: the merge command was refused with "write-pr never merges: the user runs gh pr merge"; the hook also refused a script that merely contained those words, so it matches the command text anywhere)
- [ ] 4.4 On a branch with commits, run a test command in the chat, then `/jois:write-pr`, and verify the presented PR shows that run as a `chat` bullet with only the counts the output showed and no tag in the opened body; repeat after editing a file in the diff and verify the run is reported as out of date (result: record what you saw)
- [ ] 4.5 On a branch whose group has no recorded verification and touches a directory with a documented test command, run `/jois:write-pr` in a fresh chat; verify it asks once before running anything, runs the command only after you agree, shows the result as a `chat` bullet, and on a decline falls back to asking what you ran (result: record what you saw)
