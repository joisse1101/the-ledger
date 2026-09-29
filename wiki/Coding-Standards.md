# Coding standards

What "human-understandable" means in this repo: a contributor who has never seen the code should be
able to find where something lives, read it top to bottom, and change it without breaking something
unrelated. The rules below are the ones this codebase already follows; new code matches them.

## Layout

- Four top-level service folders: `api/`, `web/`, `gateway/`, `hooks/`. All Python, tests and
  virtualenv included, lives in `api/`. See [Repository layout](Repository-Layout.md).
- One module per concern. The data layer (`api/claude_*.py`) has no FastAPI dependency, so it can be
  read and tested on its own. See [Backend: data layer](Backend-Data-Layer.md).
- One test file per module under test, named `test_<module>.py`. See [Testing](Testing.md).

## Reading the code

- Match the surrounding code: naming, comment density and idiom. Do not reformat unrelated lines.
- Names say what a thing is. Prefer a longer, clear name to an abbreviation.
- Comments explain why (a constraint, a trap, a decision), not what the next line does.
- Keep functions short enough to read without scrolling; pull pure logic out of I/O so it can be
  tested directly (for example `api/overview_stats.py` and `api/transcript_query.py`).
- Handle failure at the edge that knows what to do about it; do not swallow errors deeper down.

## Frontend

- Plain hand-written CSS, colours only from the variables in `web/src/theme/tokens.css`. New
  components use a colocated CSS module; migrate a component when you touch it, do not rewrite
  `web/src/styles/` wholesale. See [Frontend: shell and theme](Frontend-Shell-And-Theme.md).
- Views take the same data whatever the screen size; only layout changes with the viewport. See
  [Frontend: shared components](Frontend-Shared-Components.md).
- Types in `web/src/api/types.ts` mirror the server's JSON one to one. A type error fails the build.

## Documentation

- Explanation lives in `wiki/`, one topic per page, linked from `Home.md` and `_Sidebar.md`.
- Requirements live in `openspec/specs/`; wiki pages point at them and do not restate them.
- `CLAUDE.md` files hold commands, conventions and pointers only. `python check_docs.py` (run from
  `api/`) enforces links, paths and size budgets; CI runs it on every pull request.
- Link between wiki pages as `[text](Page-Name.md)`. The publish step strips the `.md` for the wiki.
- A repo path in code formatting must exist. If it is deliberately absent from a checkout (a
  gitignored file), put `<!-- docs-check: ignore -->` on that line.
