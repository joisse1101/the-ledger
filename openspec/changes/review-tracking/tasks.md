## 1. Verify and version

- [x] 1.1 Verify on a throwaway rule that Claude Code loads a rule whose frontmatter has a `metadata:` map with `version` and `last_updated` (and, scoped, `paths:` plus `metadata:`); record the result and, if rejected, switch design decision 1 to a first-line comment before continuing (result on 2.1.299: a top-level `version:` was accepted; re-verified with the nested `metadata:` map before stamping, see 1.2)
- [x] 1.1b Verify whether a subagent's frontmatter can carry a `PreToolUse` hook that denies a Read/Grep call; record the answer and, if unsupported, drop design layer 12(b) and plan the README `permissions.deny` snippet instead (result on 2.1.299: the agent hook never ran, the same hook in `settings.json` blocked; layer dropped, README snippet planned)
- [x] 1.2 Add `metadata:` with `version: "1.0.0"` and `last_updated: "<today>"` to every file in `toolkit/rules/` and to the `coding-standards` skill (`commit-hygiene.md` gets a `metadata:`-only block, no `paths:`), replacing the earlier top-level `version:` stamps, and verify scoped rules keep their `paths:` and still load
- [x] 1.3 Extend `api/check_docs.py` to require `metadata.version` (semver) and `metadata.last_updated` (date) on every skill, rule, agent and `jois-review` command, and reject a top-level `version:` (naming the file on failure), with tests in `api/tests/test_check_docs.py` for missing, malformed and valid values, a top-level `version:`, and the `commit-hygiene` `metadata:`-only block; run `cd api; pytest` and `python check_docs.py`

## 2. Shared hash helper

- [x] 2.1 Create `toolkit/skills/coding-standards/scripts/Get-ItemHash.ps1` holding the installer's hash algorithm plus a `metadata.version`/`last_updated` reader, runnable standalone, and verify it prints the same hash as the current installer for an unchanged rule
- [x] 2.2 Make `Install-Toolkit.ps1` dot-source the helper instead of its private copy, add versions (toolkit and destination) to `-List`, and verify `-List` reports no new drift on an unchanged install and shows both versions for a differing item
- [ ] 2.3 Update `toolkit/README.md` for versions, the helper and `-List` output

## 3. Review skill saves its output

- [ ] 3.1 Add the save step to `toolkit/skills/coding-standards/SKILL.md`: `reviews/YYYY-MM-DD_HHMM.md` naming with collision suffix, frontmatter fields, `uses[]` populated through the helper, coverage section, finding-block template with the five categories and symbol anchors, "what's good" section; keep it within 6 KB and bump its `metadata.version`
- [ ] 3.2 Update `check_docs.py` for the 6 KB skill budget and confirm the skill's references still resolve; verify `python check_docs.py` passes
- [ ] 3.3 Dry-run the skill on a small diff and verify the produced file matches the spec (metadata, one complete block per finding, unchecked boxes)

## 4. Read-only reviewer and baseline

- [ ] 4.1 Add an `agents` entry to `toolkit/install/targets.json` and generalise `Install-Toolkit.ps1` item discovery, install, `-List` and uninstall to a fourth kind (with `-Agent <name>`); verify with the installer against a temp `-Scope project -Path`, including the differs and foreign-agent-untouched cases
- [ ] 4.2 Create `toolkit/agents/code-reviewer.md` with `metadata:` and `tools: Read, Grep, Glob`, instructed to return findings in the finding-block shape and never to propose edits as applied; verify it installs
- [ ] 4.3 Extend `api/check_docs.py` to fail when `code-reviewer.md` is missing or lists a tool outside Read, Grep and Glob, with tests for a clean file, an added Bash and a missing file; run `pytest` and `python check_docs.py`
- [ ] 4.4 In the `coding-standards` skill, add the flow: snapshot `git status --porcelain` and `git diff`, run the baseline (record `baseline` or `not run` with reason), delegate reading to `code-reviewer` (split by directory if large), write the review, re-compare and set `tree_unchanged`; keep within 6 KB
- [ ] 4.5 Verify on a sample run: a green baseline is recorded as passed, a deliberately failing test becomes a finding, a gitignored cache does not flip `tree_unchanged`, and a touched tracked file does

## 4b. Sensitive files

- [ ] 4.6 Create `toolkit/skills/coding-standards/scripts/sensitive-paths.txt` and `Test-SensitivePath.ps1`; verify with a test that `.env`, `.env.local`, `a.pem`, `id_rsa` and `secrets.json` are denied while `.env.example`, `.env.sample` and `src/env.ts` are allowed
- [ ] 4.7 Make the skill build the reviewer's file list from `git ls-files` minus the denylist, list skipped sensitive paths by name in the coverage section, and verify a gitignored `.env` and a tracked `x.pem` are both absent from the list
- [ ] 4.8 Add the opt-in `permissions.deny` snippet for the denylist patterns to `toolkit/README.md` (1.1b showed agent hooks do not run) and verify every denylist pattern appears in it
- [ ] 4.9 Add the output scan and redaction (private-key headers, token-like strings, `KEY=value` for secret-named keys) writing `redactions: N`, and verify a seeded `API_KEY=…` quoted in a finding is replaced by a marker in the saved file

## 5. Apply and archive commands

- [ ] 5.1 Write `toolkit/commands/jois-review/apply.md` (default newest open review, next unchecked finding, locate by anchor, tests/build before ticking, `Skipped: <reason>`, stale-version warning, stop for commit-hygiene confirmation) with `metadata:` and verify by applying one finding from the 3.3 sample review
- [ ] 5.2 Write `toolkit/commands/jois-review/archive.md` (refuse on open findings, set `status`/`archived_at`, move to `reviews/archive/`, stale-version warning) with `metadata:` and verify it refuses an open review and archives a finished one
- [ ] 5.3 Verify `Install-Toolkit.ps1 -Command jois-review` installs the namespace and `/jois-review:apply` is available in a new session

## 6. Docs

- [ ] 6.1 Update `CLAUDE.md` and `wiki/Repository-Layout.md` for the `reviews/` folder (and the "six folders" wording), and `wiki/Testing.md` if it lists docs-check rules; keep `CLAUDE.md` under 8 KB
- [ ] 6.2 Run `cd api; python check_docs.py` and `pytest` and verify both pass; run `openspec validate review-tracking`
- [ ] 6.3 Refresh the global install with `Install-Toolkit.ps1 -Force` and verify `-List` shows every item up to date
