## 1. Installer supports agents and commands

- [x] 1.1 Restructure `toolkit/install/targets.json` to per-kind destinations (skills, agents, commands) and verify `Install-Skills.ps1 -List` still reads it
- [x] 1.2 Generalize the source scan and hash function in `Install-Skills.ps1` to handle a skill folder or a single `.md` file, and verify existing skills report the same state as before
- [x] 1.3 Add `-Kind` and `-Name` parameters (keeping `-Skill`), the unknown-name error listing available items, and verify each path with a temp destination
- [x] 1.4 Verify install, `-List`, differs-without-`-Force`, `-Force`, and `-Uninstall` (foreign items untouched) for skills, agents and commands using a throwaway `-Scope project -Path` folder, and confirm no `settings.json` is created or changed

## 2. Audit engine (`toolkit/skills/code-audit/scripts/audit.py`)

- [x] 2.1 Implement scope resolution (merge-base diff vs `main`, fallback to `master` then `--full`, `--full`, "nothing to audit" exit) and verify with a unit test on a temp git repo
- [x] 2.2 Implement stack detection and the Phase 0 runners (Ruff, mypy, tsc, ESLint, Clippy) with skip-if-missing, writing `phase0.json` to the evidence folder with `gate` pass or fail, and verify a file with a syntax error yields `gate: fail` and a lint-only file yields `gate: pass`
- [x] 2.3 Implement Phase 1 runners (gitleaks, semgrep, jscpd, trivy) with per-tool timeouts, writing raw and normalized JSON plus `summary.json` into an evidence folder `<repo>/code-audit/<run>/` (self-ignored by git, excluded from scope) (`ran`, `skipped` with reason, `failed`), and verify a missing tool is `skipped` and the run still exits 0
- [x] 2.4 Implement severity mapping to Critical, Medium and Low, and post-filtering of findings to the scope file list, and verify with fixture tool outputs
- [x] 2.5 Add stdlib `unittest` tests under `toolkit/skills/code-audit/scripts/tests/` for tasks 2.1 to 2.4 and verify they pass on Windows with `python -m unittest`
- [x] 2.6 Implement the read-only guards: a fixed per-tool command table with no auto-fix flags, a pre-run snapshot (`git status`, `HEAD`, content hashes of in-scope and untracked files) and `audit.py --verify`. Verify with tests that no generated command contains a fix flag, and that modifying, adding or deleting a file between snapshot and verify fails with the changed path
- [x] 2.7 Run `audit.py` against this repo (`api/` and `web/`) and verify the evidence folder is produced under `code-audit/` and `git status` ignores it, tools that are not installed are listed as skipped, and `git status` is identical before and after

## 3. Skill, agents and command

- [x] 3.1 Write `toolkit/skills/code-audit/SKILL.md` and reference files for the evidence schema, severity mapping and report format, and verify the skill folder is self-contained
- [x] 3.2 Write `toolkit/agents/sec-checker.md` with frontmatter `tools: Read, Grep, Glob` and a scoped blocking `PreToolUse` hook (scanner correlation, OWASP data-flow, false-positive dismissal with reasons, citation required) and verify its output format matches the report spec
- [x] 3.3 Write `toolkit/agents/arch-checker.md` with the same read-only `tools` allowlist and blocking hook (KISS, YAGNI, DRY from `jscpd.json` and flagged complex files, concrete refactor per finding) and verify its output format matches the report spec
- [x] 3.4 Write `toolkit/commands/code-audit.md` (phase sequencing, `--full`, gate stop, spawn both agents, merge severities with recorded adjustments, drop uncited findings, triage table with skipped tools and scope) and verify by reading it against every scenario in the `code-audit` spec
- [x] 3.5 Make the command call the snapshot before Phase 0 and `audit.py --verify` after the agents, headed "AUDIT INVALID" on any difference, and verify with a seeded tamper that the report is not shown as clean
- [x] 3.6 Spike: on the installed Claude Code version, check whether a command or skill can deny Edit and Write for its own run, and how a scoped agent `PreToolUse` hook is declared. Record the result in design.md and adopt it in the command if it works
- [x] 3.7 Red-team test: run each agent with a prompt that tells it to edit a file and run `git checkout`, and verify both attempts are blocked and `git status` is unchanged
- [x] 3.8 Install into a temp project with the installer, run `/code-audit` there on a small seeded repo (one syntax-free vulnerability, one duplicate block), and verify the report shows Critical, Medium and Low groups and the skipped-tools list

## 4. Cleanup and docs

- [ ] 4.1 Delete `toolkit/skills/toolkit-hello/` and verify the installer lists only real toolkit items
- [ ] 4.2 Update `toolkit/README.md` (quick start, `-Kind`/`-Name`, per-kind manual install table, optional scanner list with install hints) and verify a manual-only reader can follow it
- [ ] 4.3 Update `CLAUDE.md` and `wiki/Repository-Layout.md` for skills, agents and commands, and verify `cd api; python check_docs.py` passes
- [ ] 4.4 Run `openspec validate add-code-audit-toolkit --strict` and verify it reports the change valid
