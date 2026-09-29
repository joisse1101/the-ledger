**Manual checks:** tasks marked **(manual)** need someone to look at a rendered page in a browser.
The user does these by hand. The assistant does not use a browser or browser extension for them: it
prepares the change, tells the user what to look at, and waits for the user to report the result
before ticking the task.

## 1. Verify the publishing assumptions

- [x] 1.1 **(manual)** In a scratch copy of the wiki repo, push test pages using each link syntax (`[x](Page-Name)`, `[[Page-Name]]`, `.md` suffix); the user checks which work both on the GitHub wiki and when browsing `wiki/` in the repo and reports back; record the chosen syntax in the docs-contributing page (decision recorded in design.md: `.md` links, stripped on publish; add it to the docs-contributing page when that page is written in 4.4)
- [x] 1.2 Confirm Actions can push to the wiki repo with `GITHUB_TOKEN` (repo Settings > Actions > workflow permissions: read and write) and verify with a throwaway commit that is then reverted

## 2. Drift guards

- [x] 2.1 Write `api/check_docs.py` (link/route-target resolution, orphan check against `_Sidebar.md`/`Home.md`, inline-code repo-path existence with an ignore marker, size budgets 8 KB root / 4 KB nested) and verify `python check_docs.py` exits non-zero with a clear message on each failure kind
- [x] 2.2 Add `api/tests/test_check_docs.py` covering each spec scenario (renamed path, missing route target, orphan page, over-budget file, all-pass) against a temp tree, and verify `pytest` passes from `api/`
- [ ] 2.3 Add `.github/workflows/docs-check.yml` running the script on pull requests and verify it fails on a deliberately broken link in a draft PR, then passes once fixed
  - Status: workflow added; failure path confirmed on draft PR #7 (run 36538881487). Pass path deferred to 6.2, since it needs the wiki skeleton (3.2) and slim CLAUDE.md (5.1).
- [ ] 2.4 **(manual)** Add `.github/pull_request_template.md` with the docs checklist line; the user opens a new PR and confirms the checklist line appears
  - Status: template added. GitHub reads it from `main`, so verify after merge by opening any new PR.
- [x] 2.5 Add `operations.archive.guidance` to `openspec/config.yaml` asking to update the affected wiki page, and verify the config still parses (`openspec list`)

## 3. Publish workflow

- [ ] 3.1 Add `.github/workflows/wiki-publish.yml`: on push to `main` touching `wiki/**`, clone the wiki repo, warn about any commits not authored by the workflow, mirror `wiki/` (deleting removed pages, and stripping `.md` from internal link targets), push only when there is a diff, fail on push error
- [ ] 3.2 Add a `wiki/` skeleton (`Home.md` with page list and an "edit in the repo, not the wiki" note, `_Sidebar.md`) and remove the empty `wiki/docs.md`; verify the publish run succeeds (`gh run view`), then **(manual)** the user confirms on the GitHub wiki that the placeholder is replaced
- [ ] 3.3 **(manual)** Verify the web-edit path: the user makes an edit on the GitHub wiki, a further docs change is pushed, and the user confirms the run log warns and the wiki matches `wiki/` afterward
- [ ] 3.4 Verify a push to `main` with no `wiki/` changes does not trigger a publish

## 4. Move the documentation

- [ ] 4.1 Create wiki pages from `CLAUDE.md`'s Architecture > Data layer section (data layer, history store), moved verbatim then tidied; replace spec-restating text with pointers to `openspec/specs/`; verify `check_docs.py` passes
- [ ] 4.2 Create wiki pages for the backend (routes table, security, live snapshot, pending decisions, overview/query modules) and verify `check_docs.py` passes
- [ ] 4.3 Create wiki pages for the frontend (API layer, shell/theme, sessions, overview, projects, shared components) and verify `check_docs.py` passes
- [ ] 4.4 Create wiki pages for setup and run (including gateway and the history backup task), testing, gateway, hooks, and a coding-standards page stating what "human-understandable" means for this repo; verify `check_docs.py` passes
- [ ] 4.5 Cross-check that nothing from the old `CLAUDE.md` was dropped: compare its section list against the wiki page list and confirm each section landed somewhere or was intentionally removed

## 5. Slim CLAUDE.md

- [ ] 5.1 Rewrite root `CLAUDE.md` to commands, repo conventions and the area -> page routing table; verify it is under 8 KB and `check_docs.py` passes
- [ ] 5.2 Add `api/CLAUDE.md`, `web/CLAUDE.md` and `hooks/CLAUDE.md` (pointers and local rules only, under 4 KB each; none for `gateway/`); verify `check_docs.py` passes
- [ ] 5.3 Verify the payoff: start a fresh session and confirm the guidance loaded at start is the slim root file only, and that a task in `web/` picks up `web/CLAUDE.md` and reads the relevant wiki page on demand

## 6. Wrap up

- [ ] 6.1 Update `README.md` to point at the wiki and remove content now duplicated there; verify links resolve with `check_docs.py`, and **(manual)** the user clicks through them on GitHub
- [ ] 6.2 Confirm the drift guards fire end to end on one real PR (broken path, orphan page, over-budget CLAUDE.md), then archive the change
