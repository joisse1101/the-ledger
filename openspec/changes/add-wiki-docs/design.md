## Context

See proposal.md - Why. Current state: a 62 KB root `CLAUDE.md`; an empty tracked `wiki/docs.md`; a
GitHub wiki repo (`joisse1101/the-ledger.wiki.git`, branch `master`) containing only a placeholder
`Home.md`. A GitHub wiki is a separate git repo with no pull requests, and it presents pages as a
flat list: `_Sidebar.md` is the only real hierarchy and link paths differ between the wiki and repo
browsing. Repo layout rule: the root holds only `api/ web/ gateway/ hooks/` plus cross-cutting
docs/tooling, and all Python (tests included) lives in `api/`.

## Goals / Non-Goals

**Goals:**
- One source of truth for explanatory docs, reviewed with the code.
- A root `CLAUDE.md` small enough that loading it every session is cheap.
- Docs that fail CI when they rot in mechanically detectable ways.

**Non-Goals:**
- Subfolders in `wiki/`. Folders may improve human readability but are deferred; flat names with
  prefixes give grouping for now.
- Two-way sync or editing through the GitHub web UI.
- Rewriting the content for style beyond what the split needs; pages are moved and tidied, not
  reinvented.
- A manual publish script. The Action is the one publish path (can be added later).

## Decisions

**Publish direction: repo -> wiki, one way, via GitHub Action.** A workflow on `push` to `main`
filtered to `wiki/**` clones `the-ledger.wiki.git` with the built-in `GITHUB_TOKEN` (no PAT),
replaces its contents with `wiki/` (deleting removed pages), and pushes if there is a diff.
Alternatives: a submodule (two commits per change, easy to forget the bump) and two-way sync
(conflict handling for little gain).

**Detecting web edits.** Before overwriting, the workflow looks at the wiki repo's history: any
commit whose author is not the workflow's bot identity is reported as a warning listing what will be
lost. It still publishes; the repo wins.

**Flat files, hyphenated names, group by prefix.** e.g. `Backend-Data-Layer.md`,
`Frontend-Sessions.md`. `Home.md` (project summary and full page list) and `_Sidebar.md` (navigation)
are required. Links between pages use one syntax verified to work both in the wiki and when browsing
the repo (task 1.1 tested this before content is written).

**Link syntax (decided from task 1.1):** links are written `[text](Page-Name.md)`. Tested on
2026-09-29: `[text](Page-Name)` works on the wiki but 404s in the repo; `[[Page-Name]]` works only on
the wiki; `.md` (with or without `./`) works in the repo and navigates on the wiki but only as a bare
markdown render. So `wiki-publish` strips `.md` from internal link targets while mirroring, giving
normal wiki pages there while `wiki/` keeps working links. `check_docs.py` resolves the `.md` form.

**Routing, not imports.** Root `CLAUDE.md` = commands + conventions + a table `area -> wiki page`.
`@wiki/...` imports were rejected because imports are expanded into every session, which recreates the
context cost. Assistants read a page with normal file reads when a task touches its area.

**Nested `CLAUDE.md` in `api/`, `web/`, `hooks/`.** Each holds that folder's routing table and local
rules only. They load when Claude works in the folder, so a frontend session never sees backend
routing, and the root shrinks further. `gateway/` is skipped: it is small and one wiki page covers
it. `hooks/` is included because it is expected to grow. Rule to prevent a second copy of the docs:
nested files contain pointers and rules, never explanations.

**Docs check lives in `api/check_docs.py` with `api/tests/test_check_docs.py`.** It follows the
"all Python in `api/`" rule even though it checks the whole repo; it reads paths relative to the repo
root. It is plain Python, no new dependencies, runnable locally (`python check_docs.py`) and in CI.
It verifies: (1) every wiki link and every `CLAUDE.md` route target resolves to a wiki page;
(2) every wiki page is linked from `_Sidebar.md` (and `Home.md`); (3) every repo path in inline code
in a wiki page or `CLAUDE.md` exists (paths that are clearly not repo paths, such as URLs, commands
and globs, are skipped, with an explicit ignore marker for exceptions); (4) size budgets.

**Size budgets:** root `CLAUDE.md` 8 KB, each nested `CLAUDE.md` 4 KB. Budgets are constants in the
script, easy to retune; the point is that growth becomes a visible decision, not drift.

**Two workflows:** `docs-check` (on every pull request, since a code rename can break a doc path) and
`wiki-publish` (on push to `main` touching `wiki/**`).

**Human prompts:** `.github/pull_request_template.md` gets a docs checklist line;
`openspec/config.yaml` gets `operations.archive.guidance` asking for the affected wiki page update.

## Risks / Trade-offs

- [Someone edits the wiki in the browser and loses work] -> the publish step warns; docs state the
  wiki is a mirror; `Home.md` carries an "edit in the repo" note.
- [Path check has false positives on inline code that isn't a path] -> heuristics plus an explicit
  ignore marker; failures name file and path so they are quick to triage.
- [Checks catch missing paths but not wrong prose] -> accepted; PR checklist and archive guidance
  cover judgment, the script covers what is mechanical.
- [Moving 62 KB of content loses detail or duplicates specs] -> pages are moved verbatim first,
  then tidied; anything that restates a spec is replaced by a pointer to `openspec/specs/`.
- [`GITHUB_TOKEN` cannot push to the wiki unless Actions has write permission] -> the wiki already
  has a first commit; confirm the permission in task 1.2 before relying on it.
- [Nested CLAUDE.md is not loaded if a session never touches that folder] -> intended; root routing
  still names the areas.

## Migration Plan

1. Verify link syntax and the token/permissions on a throwaway wiki push. 2. Land the check script and
workflows with a first small `wiki/` (Home, Sidebar). 3. Move content page by page, shrinking
`CLAUDE.md` as each area moves, so the file is never left half-documented. 4. Publish. Rollback: the
old `CLAUDE.md` is in git history; the wiki is regenerated from `wiki/` on the next push.
