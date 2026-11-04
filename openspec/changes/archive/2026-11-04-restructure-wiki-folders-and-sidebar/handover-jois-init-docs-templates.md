# Handover: update `jois-init-docs-templates`

## Purpose

The Ledger repo now writes its wiki sidebar by hand and checks it, instead of generating it. The templates that `/jois-init:docs` installs still describe the old, generated design. This page tells whoever updates the templates what changed here and what to change there, so a later `/jois-init:docs` run does not bring the generated sidebar back.

The owner is you; no one else is assigned and no date is set. The work happens outside this repo, in the `jois-init-docs-templates` skill, which I could not read from this session.

## What changed in this repo

Five commits on the `structure-wiki` branch, all unpushed when this was written:

- `5558185` removes the sidebar generator from `scripts/build_wiki.py`, adds `check_sidebar` and a `CLAUDE.md` link check to `scripts/check_docs.py`, drops the `jois-init:docs` markers, and updates the two test files.
- `beb7809` moves the 33 wiki pages into section folders.
- `819ead5` rewrites the links between pages and five page titles.
- `6a0c891` writes `wiki/_Sidebar.md` and `wiki/Home.md` by hand.
- `7b90281` points the routing tables in the four `CLAUDE.md` files at the new pages.

The reasons and decisions are in `design.md` and `proposal.md` in this same folder.

## Why the templates must change

The old design generated `_Sidebar.md` alphabetically and a "Pages" block in `Home.md`. That list mixed section prefixes, put Glossary in the middle and could not express a reading order. A generator would need an ordering scheme (number prefixes, an order file or front matter), which is more machinery than a 33-link list needs. So the sidebar is now an ordinary page, and the check makes sure it stays complete.

If the templates stay as they are, a `/jois-init:docs` run on a repo that restores the markers overwrites the scripts with the old behavior. In this repo the markers are removed, so a rerun should leave these files alone. That is assumed from the marker design, not tested.

## What to change in the templates

### 1. The wiki builder template (`build_wiki.py`)

Remove these, as `5558185` did here:

- `page_title`, `nav_lines`, `_block`, `render_nav` and `write_nav`
- the `MD_BEGIN` and `MD_END` constants
- the `--write-nav` option and its call in `main`
- the `jois-init:docs begin/end` wrapper lines

Keep `HOME`, `SIDEBAR` and `NAV_PAGES`, because the checker imports them. Update the docstring to say that the sidebar and Home are handwritten and checked by `check_docs.py`.

### 2. The docs checker template (`check_docs.py`)

Make these changes:

- Replace `check_navigation` with `check_sidebar`: every page except `Home.md` and the sidebar is linked exactly once in `_Sidebar.md`, and every link in the sidebar resolves.
- Narrow `check_orphans` to `Home.md` only, so a page missing from the sidebar is reported once, not twice.
- Add `check_claude_wiki_links`: every link in a `CLAUDE.md` that points under `wiki/` must name an existing file, resolved relative to that file. This needs `import posixpath`.
- Wire both new checks into `check_docs`, and update the numbered list in the docstring.

The existing code in this repo is the reference implementation. Diff `scripts/check_docs.py` between `5558185~1` and `5558185` to see all of it.

### 3. The two test templates

Make these changes:

- Delete the four `write_nav` tests in the builder tests.
- In the checker tests, write the sample tree's Home and sidebar by hand instead of calling `write_nav`.
- Add tests for a page listed twice, a page missing from the sidebar, a broken sidebar link, a sidebar that links Home, and a `../wiki/Missing.md` link in a nested `CLAUDE.md` (it must report the file and line).

Two of the new tests (missing page, broken sidebar link) also pass against the old code, because the old checks already produced the same messages. Only the listed-twice and `CLAUDE.md` link tests prove the new behavior.

### 4. What the command writes into a new repo

Check what `/jois-init:docs` writes today for `wiki/Home.md`, `wiki/_Sidebar.md` and the "Where the docs are" table in `CLAUDE.md`. Each must be a starter page you edit by hand, with no generated block and no markers.

Decide whether the starter wiki should be flat or in folders. This repo uses folders (`User-Guide/`, `Contributing/`, `Backend/`, `Frontend/`, `Services/`, `Ideas/`), and the builder already supports both.

### 5. The ownership markers

Decide whether the templates keep `jois-init:docs begin/end` markers on files that a repo is expected to edit. Here they were removed so the repo owns the files. A reasonable rule: keep markers only on files the command should keep overwriting, and none on the scripts and their tests.

## What stays the same

The publish workflow `.github/workflows/wiki-publish.yml` was not changed and keeps its markers. It already runs `build_wiki.py --out`, which flattens folders to names joined by `-`. So no template change is needed for publishing.

## How to check the work

1. Run `/jois-init:docs` in a scratch repo under that repo's own `.scratch/`, never in a real one.
2. Run `python scripts/check_docs.py` there. It should pass on the starter wiki.
3. Run the tests: `cd api; pytest ../scripts/tests` in this repo's layout, or the equivalent in the scratch repo.
4. Rerun `/jois-init:docs` and confirm the scripts, Home and the sidebar are not overwritten.

## Known, assumed and unchecked

Known, from this repo's commits and test runs:

- The scripts and tests above pass (28 tests) and need no third-party packages.
- `check_docs.py` reports only 3 lines on this repo: `widget/workouts/mine` in `wiki/Backend/API-Routes.md:233`, and `web/dist` in `wiki/Contributing/Setup-And-Run.md:48` and `wiki/Services/Widget.md:128`. They are paths created at run time, and they appear identically before the move. Teach the checker about generated paths, or reword the prose, when you update the template.

Assumed:

- The template files mirror this repo's pre-change scripts, since the markers say the command installs them.
- A markerless file is left alone by a rerun of the command.

Unchecked:

- The real layout and file names inside `jois-init-docs-templates`.
- Whether other templates (a CI docs check, a pull request template, the `CLAUDE.md` starter) mention `--write-nav` or the generated block. Search the whole skill for `write-nav`, `render_nav`, `jois-init:docs begin` and `Pages` before you finish.
- Whether anything outside this repo links to the old wiki page names, which stop working when this branch merges.
