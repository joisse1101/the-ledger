## Why

`CLAUDE.md` is ~62 KB (~15k tokens) and is loaded into every chat, whatever the task. It also mixes
three different things: rules for Claude, how the system works, and what it must do. The result is
a wasteful context window and documentation that is hard for a human to read as a coding reference.
A GitHub wiki (`the-ledger.wiki.git`) already exists but holds only a placeholder `Home.md`.

## What Changes

- Move the "how the system works" content out of `CLAUDE.md` into flat, single-topic pages under
  `wiki/`, written to be read by both people and AI.
- Make the `wiki/` folder in this repo the source of truth; publish it one way to the GitHub wiki
  with a GitHub Action on push to `main`. Web edits on the GitHub wiki are not supported.
- Slim `CLAUDE.md` to setup/run/test commands, repo conventions and a routing table that says which
  wiki page to read for which area. Pages are read on demand; no `@` imports (they load eagerly).
- Add nested `CLAUDE.md` files in `api/`, `web/` and `hooks/` (not `gateway/`) holding only a
  folder-local routing table and local rules, so a chat only pays for the area it works in.
- Add drift guards: a docs check script run in CI (routing/link/orphan/code-path/size-budget), a PR
  template checklist, and `openspec/config.yaml` archive guidance to update the affected wiki page.
- Remove the empty `wiki/docs.md`; `wiki/Home.md` replaces it.
- Requirements stay in `openspec/specs/`; the wiki does not restate them.

## Capabilities

### New Capabilities
- `project-documentation`: where the project's documentation lives, how it is published, how
  `CLAUDE.md` routes to it, and the checks that keep it from drifting.

### Modified Capabilities
<!-- None: no existing app behavior changes. -->

## Impact

- New: `wiki/*.md`, `api/CLAUDE.md`, `web/CLAUDE.md`, `hooks/CLAUDE.md`, `.github/workflows/`
  (docs check, wiki publish), `.github/pull_request_template.md`, `api/check_docs.py` + its test.
- Changed: root `CLAUDE.md` (drastically shorter), `openspec/config.yaml` (archive guidance).
- Removed: `wiki/docs.md`.
- The GitHub wiki's existing `Home.md` is overwritten on first publish.
- No runtime app, API or frontend behavior changes.
