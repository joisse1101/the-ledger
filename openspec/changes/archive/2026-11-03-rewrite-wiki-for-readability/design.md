# Design

## Context

See proposal.md for why.

- **Known:** the wiki has 22 pages (`_Sidebar.md` included), about 126 KB, all flat in `wiki/`.
- **Known:** `check_docs.py` fails on a broken link, a page missing from `_Sidebar.md`, or a missing code path.
- **Known:** wiki pages must not restate requirements. Those live in `openspec/specs/`.
- **Known:** the app has these routes: Live (`/`), `overview`, `sessions`, `projects`, `files`, `settings`.
- **Assumed:** a reader of the guide is someone using the dashboard, not changing it.
- **Unchecked:** exact on-screen names of controls. Each guide page confirms them in `web/src` before using them.

## Goals / Non-Goals

Goals:
- Make every page readable by someone who has not seen the code.
- Give a person a task-by-task guide to the dashboard.

Non-goals:
- Changing code, tests or specs other than the `project-documentation` delta.
- Adding screenshots. They go stale and the docs check cannot test them.
- Restructuring the wiki into folders. The spec requires flat pages.
- A size budget for wiki pages. The goal is that people can read them, not that machines can load them cheaply. Page length follows the topic, and a page splits only when a person would find it easier to read split. The existing size budgets on `CLAUDE.md` files are unchanged.

## Decisions

### Guide pages are flat `Guide-*.md` files

The planned pages:
- `Guide-Getting-Started`
- `Guide-Overview`
- `Guide-Live-Sessions`
- `Guide-All-Sessions`
- `Guide-Projects`
- `Guide-Files`
- `Guide-Settings`
- `Guide-Remote-Access`
- `Guide-Widget`
- `Guide-Notifications` (toasts and chimes)

Why: the spec forbids subfolders, and the `Guide-` prefix keeps them together in the file list.
Alternative: one long guide page. Rejected because the spec says one topic per page and a long page is hard to scan.

### The guide and contributor pages stay separate

- The guide says what a person does and sees.
- The contributor pages keep saying how the code does it.
- Each guide page ends with a "More detail" link to the matching contributor page and spec.

Alternative: merge both on one page. Rejected because it mixes two audiences on one page, which is what makes the current pages hard to read.

### One glossary page

`Glossary.md` defines terms used across several pages. A term used on one page is defined on that page.
Alternative: define every term inline each time. Rejected because it repeats text and the copies drift apart.

### Verify each guide flow against the code before writing it

For each guide page:
1. Read the matching spec and the page component in `web/src`.
2. Take control names from the source, not from memory.
3. Mark anything that cannot be confirmed from source as "unchecked".

Alternative: run the app and click through. This stays an option for flows the source cannot settle, but reading the source is cheaper and repeatable.

### Rewrites keep facts, change shape

A rewrite splits long bullets, puts the purpose first, defines terms, and moves code detail under its own header. It does not drop facts.
- `Frontend-Sessions.md` and `Widget.md` are the largest and are split into topic headers, not into new pages, unless a header outgrows its page.
- If a split adds a page, it is linked from `Home.md` and `_Sidebar.md` in the same step.

### Order of work

1. Readability rules in `Coding-Standards.md`, and `Glossary.md`.
2. The user guide.
3. `Home.md` and `_Sidebar.md`.
4. Service pages: Widget, Gateway, Hooks.
5. Backend pages.
6. Frontend pages.
7. Remaining pages: setup, testing, layout, ideas.

Why: the rules and glossary come first because every later page depends on them. The guide comes next because it is the new value, and the guide's flows give the contributor pages something to link back to.

## Risks / Trade-offs

- [A rewrite silently drops a fact] → compare each rewritten page against the original and list any removed statement in the commit description. Reviewers read the diff page by page.
- [A guide page names a control that was renamed] → take names from `web/src` at write time and keep the page's "More detail" link to the spec so changes are traceable.
- [Large diff is hard to review] → one commit per group, following the one-concern-per-commit rule, so each group is reviewed alone.
- [Guide pages drift from the app] → the existing archive guidance already asks for a wiki update when behavior changes. No new automation is added here.

## Open Questions

None.
