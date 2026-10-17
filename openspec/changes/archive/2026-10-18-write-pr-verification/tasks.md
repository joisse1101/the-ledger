## 1. Template

- [x] 1.1 Update `toolkit/skills/write-pr/pr-template.md`: replace "Manual Test Steps" with an Author Verification subsection (bullet shape `**Label:** command or input, then the observed result`) and a How to Test This PR subsection (numbered steps, commands in fenced blocks), drop "(describe steps below)" from the Manual box, and rewrite the Automated and Manual ticking rules so Manual is ticked only when a bullet is a manual check; verify the template has no fixed counts, its code fence is closed, and the file still ends with the "No visual-proof section" rule

## 2. Verification rules

- [x] 2.1 Add `toolkit/skills/write-pr/verification.md` covering how to read `tasks.md` (verification task with a result, checked task with no result, unchecked or plain task), the ask-once rule across groups, the three kinds of reviewer step and the exists-in-checkout check, the source tags, and that tags are stripped from the body; verify every rule in the spec's two new requirements has a matching sentence and the file stays under about 3 KB
- [x] 2.2 Update `toolkit/skills/write-pr/SKILL.md`: change the Tests compose bullet to point at `verification.md`, add the ask-once turn between compose and present, show source tags in the present step and strip them before `gh pr create`, and bump `version` to `1.1.0` and `last_updated`; verify the "present and stop, call no tool" rule still reads as applying to the confirmation prompt and `SKILL.md` stays under about 5.5 KB

## 3. Docs and checks

- [x] 3.1 Update `toolkit/README.md` ("The `write-pr` skill") and the `wiki/` page that describes the skill for Author Verification, reviewer steps and `verification.md`, linking pages as `[text](Page-Name.md)`; verify no stale mention of "manual steps recorded in tasks.md" remains
- [x] 3.2 Run `cd api; pytest` and `python check_docs.py` and verify both pass
- [x] 3.3 Run `toolkit\install\Install-Toolkit.ps1 -Skill write-pr -Scope project -Path <temp>` and verify the whole folder, including `verification.md`, is copied and `-List` shows the new version
