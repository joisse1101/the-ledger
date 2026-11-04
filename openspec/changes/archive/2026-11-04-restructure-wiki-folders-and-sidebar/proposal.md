# Proposal

## Why

The wiki has 33 pages in one flat folder, and its sidebar is a generated alphabetical list. That list mixes `Guide:`, `Backend:` and `Frontend:` pages, puts Glossary in the middle and Setup and run at the end, and `Home.md` repeats every page in a second flat list. A reader cannot see what is where, so pages are hard to find. The build script already supports pages in folders (it flattens them on publish), so the structure can be fixed without new tooling for the GitHub wiki.

## What Changes

- Move the pages into folders: `User-Guide/`, `Contributing/`, `Backend/`, `Frontend/`, `Services/` and `Ideas/`. `Home.md`, `Glossary.md` and `_Sidebar.md` stay at the `wiki/` root.
- Drop the section prefix from file names inside a folder, so `Guide-Files.md` becomes `User-Guide/Files.md`. The published name is still the path joined with `-`, for example `User-Guide-Files`.
- Rename the four Frontend screen pages to "Overview page", "Sessions page", "Projects page" and "Files page" (file name, page title and link text). Rename Backend "Overview and queries" to "Stats and queries". User-guide pages keep their plain names.
- Write `_Sidebar.md` by hand, with sections and an order that follow how a reader uses the wiki: Home, Glossary, User guide, Contributor docs (Set up, Backend, Frontend, Services), Ideas. Link text has no `Guide:`, `Backend:` or `Frontend:` prefix.
- Stop generating the sidebar and the "Pages" block. Remove the `--write-nav` option and the generated block in `Home.md`; `Home.md` stays handwritten and follows the same order.
- Replace the "navigation is up to date" check with checks on the handwritten sidebar: every page appears in it exactly once, and every link in it resolves.
- Update the wiki links in the root `CLAUDE.md`, `api/CLAUDE.md` and `hooks/CLAUDE.md` (31 in total) and every link between wiki pages to the new paths. Archived OpenSpec changes keep their old paths because they record history.
- **BREAKING:** every published wiki page name changes, and the publish job deletes the old pages (`rsync --delete`), so old wiki URLs and bookmarks stop working.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `project-documentation`: pages are grouped in folders instead of flat, the sidebar is handwritten in a logical order and checked rather than generated, the user guide lives in `User-Guide/`, and the docs check also verifies links from `CLAUDE.md` files.

## Impact

- `wiki/`: all 33 pages move or are edited (links, and four page titles); `Home.md` and `_Sidebar.md` are rewritten.
- `scripts/build_wiki.py` and `scripts/check_docs.py`, with their tests in `scripts/tests/`. Both files carry `jois-init:docs` markers that say edits are overwritten when `/jois-init:docs` is run again, so the change needs a decision on who owns them afterwards (see design).
- `CLAUDE.md`, `api/CLAUDE.md`, `hooks/CLAUDE.md`: routing-table links.
- `openspec/specs/project-documentation/spec.md`, updated when this change is archived.
- The GitHub wiki: the next push to `main` republishes it under the new names.
- Observed: `check_docs.py` checks inline-code paths in `CLAUDE.md` files but not their wiki links, even though the existing spec says it should. Without a fix, stale links after this move would go unnoticed.
