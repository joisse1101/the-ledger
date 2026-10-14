## Why

The `coding-standards` skill produces a good review, but only as chat text: it is lost when the
session ends, cannot be ticked off, and says nothing about which skill and rule versions produced
it. A whole-codebase review yields ~18 findings that take many sessions to fix; without a saved,
trackable checklist they get forgotten or re-reviewed from scratch.

## What Changes

- `coding-standards` always saves its review to `reviews/YYYY-MM-DD_HHMM.md` in the repo root. The
  file has YAML metadata (date and time, scope, git commit, skills and rules used with version and
  hash), a coverage section, one block per finding, and a "what's good" section.
- Each finding block has: item number and title, category (Rule-breaking, Defect, Structure,
  Script, Smell), affected files and lines plus a symbol anchor, problem, proposed fix, and a
  `- [ ]` checkbox.
- New command `/jois-review:apply`: works through the open findings one at a time, one commit per
  finding, ticking each box.
- New command `/jois-review:archive`: checks every finding is resolved (or skipped with a reason),
  stamps the review archived and moves it to `reviews/archive/`.
- Every skill, rule and `jois-review` command gets a `version:` in its frontmatter (a date such as
  `2026-10-14`). A review records each used item's version and content hash; `apply` and `archive`
  warn when the installed item no longer matches (stale review).
- The review is read-only: a new `code-reviewer` agent (tools: Read, Grep, Glob only) does the
  reading, and the main thread only writes the `reviews/` file. A before/after `git status`
  check proves nothing else changed and is recorded in the metadata.
- The reviewer cannot read sensitive files such as `.env`: its file list is `git ls-files` minus a
  denylist, the agent is told never to open denylisted paths (agent-level hooks do not run, so the
  README offers an opt-in `permissions.deny` snippet for a hard block), and the saved review is
  scanned and redacted so no secret reaches the committed `reviews/` folder.
- A baseline of the project's tests and build runs by default, on the main thread, before the
  review; results go in the metadata and a failure becomes a finding.
- The installer learns a fourth item kind, `agents` (`~/.claude/agents`, `<project>/.claude/agents`).
- A shared hashing helper replaces the private one in `Install-Toolkit.ps1`; `-List` also shows
  each item's version.
- `reviews/` joins the repo's cross-cutting root folders; `CLAUDE.md` and
  `wiki/Repository-Layout.md` are updated, and `check_docs.py` checks the new frontmatter.

## Capabilities

### New Capabilities
- `review-tracking`: saved review files (location, naming, metadata, finding format), the
  apply and archive commands, and version/hash staleness detection.

### Modified Capabilities
- `toolkit-coding-standards`: the review skill gains a save-to-file output and its size budget
  rises; every rule and skill carries a `version:` frontmatter key, which the docs check validates.
- `toolkit-skills`: the installer shares one hashing helper, lists item versions, gains an
  `agents` item kind, and `toolkit/commands/` gains the `jois-review` namespace.

## Impact

- `toolkit/skills/coding-standards/SKILL.md` (+ new `scripts/` helper), all of `toolkit/rules/*.md`
  (one frontmatter line each), new `toolkit/commands/jois-review/{apply,archive}.md`,
  new `toolkit/agents/code-reviewer.md`, `toolkit/install/Install-Toolkit.ps1` and `targets.json`,
  `toolkit/README.md`.
- `api/check_docs.py` and `api/tests/test_check_docs.py`; `CLAUDE.md`, `wiki/Repository-Layout.md`,
  `wiki/Testing.md` if it lists checks.
- Unverified: that Claude Code tolerates an extra `version:` key in rule frontmatter (first task).
- Not affected: the dashboard (`api/`, `web/`, `widget/`, `gateway/`) behaviour.
