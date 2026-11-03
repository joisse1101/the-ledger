# Proposal

## Why

The wiki is hard to read and has no user guide.

- Every page is written for someone changing the code, so a person who only wants to use the dashboard has nowhere to start.
- Some pages are walls of text. `Frontend-Sessions.md` is one 5 KB bullet, and `Widget.md` is 18 KB of component names.
- The repo's only docs rules cover links, paths and size budgets. Nothing says a page must be readable.

## What Changes

- Add a **User guide**: flat `Guide-*.md` wiki pages, one per task a person does with the dashboard.
- Rewrite all 22 existing wiki pages to the readability rules below. The `Home.md` rewrite also adds the User guide section.
- Add the readability rules to `Coding-Standards.md` under "Documentation".
  - Purpose or result first.
  - One header per topic, nested by hierarchy.
  - One idea per short bullet.
  - A technical term is defined on first use, or linked to a glossary page.
  - Known, assumed and unchecked facts are marked apart.
- Add a `Glossary.md` page for terms used across pages (session, live session, Remote mode, relay hook, compact and so on).
- Link every new page from `Home.md` and `_Sidebar.md`, under a "User guide" heading.
- Facts do not change. A rewrite reorders, splits and explains; it never alters what a page says the code does.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `project-documentation`: adds a requirement that wiki pages follow the readability rules, and a requirement that the wiki has a user guide covering each task a person does with the dashboard.

## Impact

- Files: everything under `wiki/` (22 rewritten, about 10 new), and the "Documentation" section of `wiki/Coding-Standards.md`.
- Code and tests: none change.
- Checks: `api/check_docs.py` must still pass, covering links, sidebar coverage and referenced paths. The new pages join its checks automatically.
- Publishing: the publish workflow mirrors the new pages to the GitHub wiki on the next push to `main`.
- Unchecked: whether the guide flows match the running app. Each guide page is verified against the code and its spec as it is written.
