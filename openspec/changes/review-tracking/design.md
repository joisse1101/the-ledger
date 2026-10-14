## Context

See proposal.md for motivation. Current state: `coding-standards` is a 3 KB chat-only checklist;
rules and skills have no version; `Install-Toolkit.ps1` has a private `Get-ItemHash` (SHA-256 over
relative paths and contents) used only for `up to date` / `differs`; `api/check_docs.py` validates
toolkit budgets and `paths:` frontmatter; the `opsx:*` commands are OpenSpec-generated copies in
`toolkit/commands/opsx/` and are not ours to version. Commit-hygiene (unscoped rule) forbids
committing without a confirmation word and wants one concern per commit.

## Goals / Non-Goals

**Goals:**
- A review is a durable file that doubles as a task list and survives across sessions.
- A reader can tell which skill and rule versions made a review, and whether they changed since.
- Fixing findings reuses the commit-hygiene flow instead of bypassing it.

**Non-Goals:**
- Automatically re-running a stale review (the user decides).
- Versioning the `opsx:*` commands or hooks.
- A hard sandbox: blocking the main thread's write tools or editing `settings.json`.
- Making the review file machine-queried by the dashboard.
- Support for tools other than Claude Code.

## Decisions

**1. Version = `metadata.version` (semver) + `metadata.last_updated`, plus a content hash recorded
in the review.** The Agent Skills format keeps a skill's version inside a flat string map,
`metadata:`, not as a top-level key, so we follow it for every item kind. Semver says how big a
change was, `last_updated` says when, both are hand-bumped, and the hash catches edits where
nobody bumped them. Staleness = version, date or hash differs. *Alternatives:* a date only (no
sense of size); semver only (no date); a top-level `version:` (not the spec's place for it; an
earlier draft used it and was reworked). The docs check validates the formats, since it cannot
know whether an edit warranted a bump.

**2. One hash helper, owned by the skill.** The review must run in any project, where the
installer may not exist, and the skill folder must stay self-contained. So the algorithm moves to
`toolkit/skills/coding-standards/scripts/Get-ItemHash.ps1` and `Install-Toolkit.ps1` dot-sources
it from the toolkit tree. Algorithm unchanged, so existing installs do not read as drifted.
*Alternative:* duplicate the code in both places and test they agree; rejected as two copies to
keep in step. The helper also prints an item's `metadata.version` and `last_updated` so reviews and `-List` share them.

**3. Review-time lookup of "what was used".** The skill hashes `~/.claude/skills/coding-standards`
and every rule actually relevant to the reviewed files (the rules whose `paths:` match, plus the
unscoped ones that were applied), from the installed copies, since those are what Claude loaded.
Project-scope installs (`<project>/.claude/...`) take precedence when present.

**4. Review file format.** YAML frontmatter (machine-readable: `reviewed_at`, `scope`, `commit`,
`status`, `uses[]`), then sections. Each finding is a `### N. Title` block with bold-label lines
and a trailing `- [ ] Done` checkbox, mirroring the tasks.md convention so a tick is a one-line
edit. Line ranges are recorded as found, plus a `symbol:` anchor per location because line numbers
go stale after the first fix. The `commit` SHA tells a human what the lines meant.

**5. Commands, not skills, for apply/archive.** They are user-invoked procedures like `opsx:*`,
so they live in `toolkit/commands/jois-review/` as `/jois-review:apply` and `/jois-review:archive`.
The own namespace avoids the built-in `/review` and `/code-review`.

**6. Apply defers to commit-hygiene.** One finding = one concern = one commit. Apply fixes, runs
tests/build, ticks the box *in the same staged change* (a review file edit is documentation of
that change), proposes the commit with a confirmation word and ends the turn. The next
invocation continues from the next unchecked item. A finding that is too large gets split into
sub-items in the file, not in one commit.

**7. Archive refuses open work.** `Skipped: <reason>` is the only alternative to a tick, which
keeps "resolved" honest. Archive moves to `reviews/archive/` (mirrors `openspec/changes/archive`)
and, being a move, is its own concern/commit.

**8. `reviews/` is root-level and tracked.** It lives beside `wiki/` and `openspec/` as
cross-cutting records, not a seventh service; the "exactly six folders" wording in `CLAUDE.md`
and `wiki/Repository-Layout.md` is updated to say reviews live in `reviews/`. Not gitignored:
they are the project's work history.

**9. Read-only by structure, verified by diff.** The `coding-standards` skill delegates the
reading to `toolkit/agents/code-reviewer.md` (tools: Read, Grep, Glob; no Edit, Write or Bash),
and only the main thread writes `reviews/<date>.md`. Before the baseline the skill snapshots
`git status --porcelain` plus `git diff`; after the review it compares. `git status` already
omits ignored files, so test caches and build output do not trip it, while a tracked file
modified by a test run does, correctly. The result is `tree_unchanged` in the metadata.
*Alternatives:* a `settings.json` deny rule or PreToolUse hook (a hard block, but the installer
must never touch `settings.json` and it would restrict the whole session); plan mode (blocks
writing the review file too); instruction only (no enforcement). The main thread keeps its write
tools, so this is structure plus detection, not a sandbox, and the spec says so by naming the check
rather than promising isolation.

**10. Baseline first, on the main thread, always.** The reviewer agent cannot run commands, so
the skill runs the project's test and build commands itself before delegating (found from
`CLAUDE.md` or the config; if none, `not run` with a reason). Results go in `baseline`. A failure
is a finding, not an abort: a red baseline is information the review should carry. The snapshot in
decision 9 is taken before the baseline, so a test run that dirties tracked files is caught.

**11. Agents as a fourth installer kind.** `targets.json` gains an `agents` entry and the
installer's item discovery generalises from three kinds to four. Each agent is one `.md` file,
like a rule. `check_docs.py` additionally fails if `code-reviewer.md` lists any tool outside
Read, Grep and Glob.

**12. Sensitive files: scope by git, deny by list, scan the output.** An agent's `tools:` list
cannot be limited by path, and hard path blocking is `permissions.deny` or a hook in
`settings.json`, which the installer must not touch. Verified on Claude Code 2.1.299: a
`PreToolUse` hook in a subagent's own frontmatter never runs, while the same hook in
`settings.json` blocks the call. So three layers, strongest first: (a) the reviewer only gets
`git ls-files` minus a denylist, which already drops gitignored `.env`; (b) the agent is told
never to open denylisted paths; (c) the finished review text is scanned and redacted before it is
written, because `reviews/` is committed and that is where a leak would persist. The denylist is
one file, `scripts/sensitive-paths.txt`, read by the list builder and the scanner, and the README
documents an opt-in `permissions.deny` snippet generated from the same patterns for users who want
a hard block. *Alternatives:* a settings hook installed by the toolkit (violates the installer
rule); a gitleaks-only scan (needs an external tool; `code-audit` already uses it but this skill
must be self-contained).

## Risks / Trade-offs

- [No hard block on the agent's reads] -> Agent frontmatter hooks do not run (verified), so the
  hard block is the user's opt-in `permissions.deny`; (a), (b) and (c) reduce the risk by default.
- [Pattern-based redaction misses an unusual secret, or redacts harmless text] -> It is the last
  line of defence, not the only one; false positives cost a marker, false negatives are bounded by
  (a) keeping the file out of scope in the first place.
- [Grep takes a path or glob, so the agent could search a directory containing a denied file]
  -> The instruction and the output scan; the opt-in `deny` snippet blocks it outright.

- [A review of a large codebase may exceed one agent's context] -> The skill may split the work
  across several `code-reviewer` calls by directory and merge the findings; the agent itself is
  stateless.
- [The main thread could still edit code] -> Accepted; the diff check detects it and records it.
- [Baseline can be slow or need a service] -> It is the project's own documented command; if it
  cannot run, the review says `not run` and why rather than silently skipping.

- [Claude Code may reject or warn on an unknown key in rule frontmatter] -> First task
  verifies on a throwaway rule; fallback is a `<!-- version: ... -->` comment on the first line
  and the helper/check read that instead. Decide before touching every rule.
- [Adding frontmatter to `commit-hygiene.md` could be mistaken for scoping] -> The docs check
  already fails on a `paths:` key there; add a test that a `metadata:`-only block passes.
- [Skill grows past 4 KB] -> Budget raised to 6 KB in the spec; the format template lives in the
  skill, the procedure details in the commands.
- [Hand-bumped versions get forgotten] -> The hash still flags the change; the version is a
  convenience, not the only signal.
- [Large reviews make big files and `apply` re-reads them] -> Acceptable; one file per review,
  and `apply` reads only metadata plus the next open block.
- [PowerShell-only helper] -> Matches the repo (Windows, PowerShell installer); noted in the
  README as a Windows limitation.

## Migration Plan

1. Verify frontmatter tolerance; bump-stamp all rules, the skill and the new commands with
   today's date.
2. Move the hash helper; confirm `Install-Toolkit.ps1 -List` shows no new drift on an unchanged
   install.
3. Re-run `Install-Toolkit.ps1 -Force` to refresh the global copies (the version lines make every
   rule `differs` once).
4. Rollback: revert the commits; saved `reviews/` files are inert Markdown.

## Open Questions

- Whether `-List` should exit non-zero on version drift (useful for CI); deferrable, default is
  informational only.
