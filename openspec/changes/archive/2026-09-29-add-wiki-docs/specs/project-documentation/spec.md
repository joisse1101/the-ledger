## Purpose

Keeps the project's documentation readable by people and cheap for AI assistants to load, by holding it in one versioned place, publishing it to the GitHub wiki, and checking that it stays in step with the code.

## ADDED Requirements

### Requirement: The repository's wiki folder is the source of truth
The project's explanatory documentation SHALL live in the `wiki/` folder of this repository and be
reviewed together with the code it describes. The GitHub wiki SHALL be a one-way mirror of that
folder: content flows from the repository to the wiki and never back. Requirements SHALL continue
to live in `openspec/specs/`, and wiki pages SHALL NOT restate them.

#### Scenario: A docs change is merged
- **WHEN** a change touching `wiki/` is pushed to `main`
- **THEN** the GitHub wiki is updated to match the `wiki/` folder exactly, including removing pages
  that no longer exist in it

#### Scenario: A change without docs changes is merged
- **WHEN** a push to `main` touches nothing under `wiki/`
- **THEN** the GitHub wiki is not modified

#### Scenario: The wiki was edited on GitHub
- **WHEN** the GitHub wiki holds commits that did not come from the publish step
- **THEN** the publish step reports that those edits are being overwritten, and still publishes

#### Scenario: Publishing fails
- **WHEN** the publish step cannot push to the GitHub wiki
- **THEN** the workflow run fails visibly rather than succeeding silently

### Requirement: Wiki pages are flat, single-topic and navigable
Each wiki page SHALL cover one topic and be stored as a file directly in `wiki/` (no subfolders).
`wiki/Home.md` SHALL describe the project and list every page, and `wiki/_Sidebar.md` SHALL link
every page, so that no page is unreachable.

#### Scenario: A new page is added
- **WHEN** a page is added to `wiki/` without being linked from `_Sidebar.md`
- **THEN** the docs check fails and names the orphan page

### Requirement: CLAUDE.md routes to the wiki instead of holding it
The root `CLAUDE.md` SHALL contain only the commands and conventions needed in every session and a
routing table naming, for each area of the codebase, the wiki page to read. Assistants SHALL read a
page on demand when a task touches that area. `CLAUDE.md` files SHALL NOT use `@` imports of wiki
pages, since imports are loaded into every session.

#### Scenario: Task in one area
- **WHEN** a session works only on files under `web/`
- **THEN** the guidance loaded for it is the root `CLAUDE.md` plus `web/CLAUDE.md`, and no
  backend page is loaded unless the task needs it

#### Scenario: Size budget exceeded
- **WHEN** the root `CLAUDE.md` or a nested `CLAUDE.md` grows past its size budget
- **THEN** the docs check fails and reports the file and its size

### Requirement: Nested CLAUDE.md files hold pointers and local rules only
`api/`, `web/` and `hooks/` SHALL each have a `CLAUDE.md` containing a routing table for that folder
and rules that apply only there. They SHALL NOT contain explanatory documentation, which lives in the
wiki. `gateway/` SHALL NOT have one.

#### Scenario: Documentation appears in a nested file
- **WHEN** a nested `CLAUDE.md` exceeds its size budget
- **THEN** the docs check fails, prompting the content to move to a wiki page

### Requirement: Documentation references are mechanically checked
A docs check SHALL run on every pull request and fail when: a route target or link in any
`CLAUDE.md` or wiki page points at a wiki page that does not exist; a wiki page is not linked from
`_Sidebar.md`; or a repository path written in code formatting in a `CLAUDE.md` or wiki page does
not exist.

#### Scenario: A file is renamed
- **WHEN** `api/security.py` is renamed but a wiki page still references `api/security.py`
- **THEN** the docs check fails and names the page and the missing path

#### Scenario: A route target is missing
- **WHEN** a routing table row points at a wiki page that does not exist
- **THEN** the docs check fails and names the file and the row

#### Scenario: Everything resolves
- **WHEN** every link, route target and referenced path resolves
- **THEN** the docs check passes

### Requirement: Contributors are prompted to update docs
Pull requests SHALL show a checklist item asking whether behavior changed and the affected wiki page
was updated. Archiving an OpenSpec change SHALL be guided, through the project's OpenSpec
configuration, to update the affected wiki page.

#### Scenario: Opening a pull request
- **WHEN** a pull request is opened
- **THEN** its description includes the documentation checklist item

#### Scenario: Archiving a change
- **WHEN** an OpenSpec change that alters documented behavior is archived
- **THEN** the archive guidance directs the archiver to update the affected wiki page
