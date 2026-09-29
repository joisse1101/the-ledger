## 1. Toolkit skeleton

- [x] 1.1 Create `toolkit/skills/` with a sample `toolkit-hello/SKILL.md`
- [ ] 1.2 Create `toolkit/install/targets.json` with the `claude-code` entry (global and project-relative skills paths)

## 2. Installer

- [x] 2.1 Write `toolkit/install/Install-Skills.ps1`: read `targets.json`, resolve global/project destination, copy one or all skills
- [ ] 2.2 Add content-hash drift detection: report up to date / differs / missing, skip differing unless `-Force`
- [ ] 2.3 Add `-List` (status per skill) and `-Uninstall` (toolkit-owned skills only)
- [ ] 2.4 Reject an unknown `-Skill` with the list of available names, copying nothing

## 3. Docs

- [x] 3.1 Write `toolkit/README.md`: quick start (get the toolkit, install everything) and a separate Skills section with the manual copy path
- [ ] 3.2 Update `CLAUDE.md`: five top-level folders, describe `toolkit/`

## 4. Verification

- [x] 4.1 Install the sample skill to a throwaway project path, then run `-List`, edit it to confirm "differs" and no overwrite, then `-Force`, then `-Uninstall`
- [ ] 4.2 Confirm a foreign skill in the destination survives uninstall and no `settings.json` changed
- [ ] 4.3 Run `openspec validate add-toolkit-skills`
