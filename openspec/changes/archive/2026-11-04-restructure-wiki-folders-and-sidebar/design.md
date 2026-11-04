# Design

## Context

See proposal.md for why. What exists today, observed in the repo:

- `scripts/build_wiki.py` already treats `wiki/` as nested. A page's published name is its path with folders joined by `-`, and `--out` rewrites relative `.md` links to those names. Nothing about the publish job needs to change.
- The same script also generates `_Sidebar.md` (flat, alphabetical, titles from each page's first `# ` heading) and a "Pages" block inside `Home.md`. `check_docs.py` fails when either differs from what the script would write.
- `check_docs.py` checks that every page is linked from both `Home.md` and `_Sidebar.md`, but it does not check wiki links inside `CLAUDE.md` files, only inline-code paths there. The existing spec says it should check them.
- Both scripts and their tests, and the publish workflow, carry `jois-init:docs begin/end` markers meaning "managed by `/jois-init:docs`; edits are overwritten".
- `Home.md` already has handwritten sections (User guide, Contributor pages) that list every page, so removing its generated "Pages" block loses no links.

## Goals / Non-Goals

**Goals:**
- A sidebar a reader can scan: grouped, logically ordered, short link text.
- The docs check still catches orphan pages and broken links, and now catches a page listed twice.
- No page is lost or left unlinked by the move.

**Non-Goals:**
- No new page content, and no section landing pages (dropped in discussion).
- No collapsible sidebar sections. Whether GitHub's wiki sidebar renders `<details>` is unchecked, so the sidebar uses plain nested lists.
- No redirects from the old published names. GitHub wikis have none, and the publish job deletes the old pages.

## Decisions

### Folders decide published names; the sidebar decides order

Pages move into `User-Guide/`, `Contributing/`, `Backend/`, `Frontend/`, `Services/` and `Ideas/`, with capitalized folder names because GitHub builds a page's title from its file name. The section prefix leaves the file name (`Backend-Data-Layer.md` becomes `Backend/Data-Layer.md`) since the folder now says it. The published name stays the same shape (`Backend-Data-Layer`) for pages that already followed the prefix convention; the pages that gain a prefix are the ones that had none:

| Old file | New file | Published name |
| --- | --- | --- |
| `Guide-*.md` (10) | `User-Guide/*.md`, e.g. `Widget.md` | `User-Guide-Widget` |
| `Setup-And-Run`, `Testing`, `Repository-Layout`, `Coding-Standards` | `Contributing/` | `Contributing-Setup-And-Run`, ... |
| `Backend-*.md` (6) | `Backend/*.md`; `Overview-And-Queries` becomes `Stats-And-Queries` | `Backend-Stats-And-Queries` |
| `Frontend-*.md` (7) | `Frontend/*.md`; `Overview`, `Sessions`, `Projects`, `Files` become `Overview-Page`, `Sessions-Page`, `Projects-Page`, `Files-Page` | `Frontend-Overview-Page` |
| `Gateway`, `Hooks`, `Widget` | `Services/` | `Services-Widget` |
| `Alert-Tiering-Ideas` | `Ideas/Alert-Tiering.md` | `Ideas-Alert-Tiering` |

`Services/Widget.md` and `User-Guide/Widget.md` do not collide (`Services-Widget` and `User-Guide-Widget`), and the existing collision check would stop the build if two pages ever did.

Use `git mv` for every move so history follows the files.

Alternative considered: keep the files flat and only hand-write the sidebar. It avoids breaking URLs, but you chose folders in discussion because the file list should also show what belongs where.

### The sidebar is handwritten and checked, not generated

`_Sidebar.md` becomes an ordinary page. Generation cannot express the order (logical, with a section's first page chosen by hand), and any ordering scheme added to the generator (number prefixes in file names, an order file, front matter) is more machinery than a 33-link list needs. Instead:

- In `build_wiki.py`, remove `nav_lines`, `render_nav`, `write_nav`, `page_title`, the marker block helpers and the `--write-nav` option. Nothing else uses them, so they are dead code.
- In `check_docs.py`, replace `check_navigation` with `check_sidebar`: every page except `Home.md` and `_Sidebar.md` is linked exactly once in `_Sidebar.md`, and every link in it resolves. The existing `check_orphans` stays and still requires `Home.md` to link every page too.
- `Home.md` loses its generated block and keeps its handwritten sections, reordered to match the sidebar.
- The sidebar uses bold section labels and nested bullets: `**User guide**`, then `**Contributor docs**` with sub-labels Set up, Backend (api/), Frontend (web/) and Services, then `**Ideas**`. Whether GitHub renders the nesting well is assumed from standard markdown, not checked.

Alternative considered: keep generating and sort by a hand-written list in the script. It leaves two places to edit for every new page and a script that holds page names.

### CLAUDE.md links are checked

Add a check that every link in a `CLAUDE.md` whose target is under `wiki/` points at an existing page, resolved relative to the file (`../wiki/...` in nested files). This closes the gap between the spec and the script, and it is what makes the 31 link edits safe: a missed one fails the check.

### Link text and links are rewritten by script, then reviewed

The wiki has about 33 pages with relative links to each other, all of which change. A one-off script (kept in `.scratch/`, deleted afterwards) maps old file to new file and rewrites every `](Old.md#anchor)` to the new relative path, keeping anchors. Where a link's visible text equals the old file stem (the `CLAUDE.md` tables use `[Backend-Data-Layer](...)`), it is updated to the new name by hand or by the same script. `check_docs.py` is then the verification, since it fails on any link that does not resolve.

### Ownership of the managed files

`build_wiki.py`, `check_docs.py`, their tests and the publish workflow are marked as managed by `/jois-init:docs`, so running that command again would overwrite this change. Decision: remove the `jois-init:docs` markers from `build_wiki.py`, `check_docs.py` and their two test files, so the repo owns them from here, and say so in each docstring. The publish workflow is not changed and keeps its markers. Follow-up outside this repo: update the `jois-init-docs-templates` templates to the same design, or the next `/jois-init:docs` run will bring the old behavior back if the markers are restored.

## Risks / Trade-offs

- [Every published wiki URL changes and old pages are deleted] → Accept it, since the wiki is a mirror with few outside links as far as the repo shows; note it in the PR description. Unchecked: whether anything outside the repo links to wiki pages.
- [A missed link or `CLAUDE.md` row after the move] → The new `CLAUDE.md` link check and the existing wiki link check fail on it; run `python scripts/check_docs.py` before finishing.
- [The sidebar drifts from `Home.md` over time] → Both must list every page (the orphan check), but their order is not compared. Accepted: Home groups by purpose and the sidebar by reading order, and a small drift costs little.
- [Someone reruns `/jois-init:docs` and overwrites the scripts] → The markers are removed (see above), and the follow-up on the templates is recorded.
- [Page titles: GitHub shows the file name as the title] → The new names are capitalized and hyphenated like the old ones; titles inside pages stay the `# ` heading.

## Migration Plan

1. Work in this worktree on the `structure-wiki` branch; nothing publishes until the branch merges to `main`.
2. Move and rename the files, rewrite links, rewrite `Home.md` and `_Sidebar.md`, update `CLAUDE.md` files.
3. Change the two scripts and their tests, then run `python scripts/check_docs.py` and `cd api; pytest ../scripts/tests`.
4. On merge, the publish job rebuilds the wiki under the new names and deletes the old ones. Rollback is reverting the merge commit, which republishes the old names.
5. Archive the change, which updates `openspec/specs/project-documentation/spec.md`.
