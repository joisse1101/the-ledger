# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Wiki pages are flat, single-topic and navigable`
- TO: `### Requirement: Wiki pages are single-topic, grouped in folders and navigable`

## MODIFIED Requirements

### Requirement: Wiki pages are single-topic, grouped in folders and navigable
Each wiki page SHALL cover one topic and be stored in a folder under `wiki/` named for its section (`User-Guide`, `Contributing`, `Backend`, `Frontend`, `Services`, `Ideas`). `Home.md`, `Glossary.md` and `_Sidebar.md` SHALL sit directly in `wiki/`. `wiki/Home.md` SHALL describe the project and list every page, and `wiki/_Sidebar.md` SHALL link every page, so that no page is unreachable. The published name of a page SHALL be its path under `wiki/` with the folders joined by `-`.

#### Scenario: A new page is added
- **WHEN** a page is added under `wiki/` without being linked from `_Sidebar.md`
- **THEN** the docs check fails and names the orphan page

#### Scenario: A page is published
- **WHEN** `wiki/User-Guide/Getting-Started.md` is published to the GitHub wiki
- **THEN** it appears there as `User-Guide-Getting-Started`, and links to it from other pages point at that name

### Requirement: Documentation references are mechanically checked
A docs check SHALL run on every pull request and fail when: a link in any `CLAUDE.md` or wiki page points at a wiki page that does not exist; a wiki page is not linked from `_Sidebar.md`, or is linked there more than once; a link in `_Sidebar.md` does not resolve; or a repository path written in code formatting in a `CLAUDE.md` or wiki page does not exist.

#### Scenario: A file is renamed
- **WHEN** `api/security.py` is renamed but a wiki page still references `api/security.py`
- **THEN** the docs check fails and names the page and the missing path

#### Scenario: A route target is missing
- **WHEN** a routing table row in a `CLAUDE.md` points at a wiki page that does not exist
- **THEN** the docs check fails and names the file and the row

#### Scenario: A page is listed twice in the sidebar
- **WHEN** `_Sidebar.md` links the same page under two sections
- **THEN** the docs check fails and names the page

#### Scenario: Everything resolves
- **WHEN** every link, route target and referenced path resolves, and each page appears once in the sidebar
- **THEN** the docs check passes

### Requirement: Wiki pages follow the readability rules
Every wiki page SHALL put its purpose or result first, give each topic its own header nested by hierarchy, and keep each bullet to one idea in one short sentence. A technical term SHALL be defined where it is first used, or link to the glossary page. The rules SHALL be written in `wiki/Contributing/Coding-Standards.md`.

#### Scenario: A reader opens any page
- **WHEN** a reader opens a wiki page
- **THEN** the first paragraph says what the page covers or what the reader can do with it

#### Scenario: A page uses a term specific to the project
- **WHEN** a page uses a term such as "Remote mode" or "relay hook"
- **THEN** the page defines it in a short phrase at first use, or links to its entry in `wiki/Glossary.md`

#### Scenario: A reader looks up the rules
- **WHEN** a contributor opens "Documentation" in `wiki/Contributing/Coding-Standards.md`
- **THEN** it lists the readability rules next to the link and size rules

### Requirement: The wiki has a user guide
The wiki SHALL include a user guide made of the pages in `wiki/User-Guide/`, one per task a person does with the dashboard. The guide SHALL cover starting and signing in, the Overview, Live sessions, All sessions, Projects, Files, Settings, Remote access from another device, the desktop widget, and notifications. `Home.md` and `_Sidebar.md` SHALL list the guide pages under a "User guide" heading.

#### Scenario: A person wants to use the dashboard
- **WHEN** a person opens `Home.md`
- **THEN** they see a "User guide" section linking to each guide page, before any contributor-facing section

#### Scenario: A guide page is added without a link
- **WHEN** a page in `wiki/User-Guide/` is not linked from `_Sidebar.md`
- **THEN** the docs check fails and names the orphan page

## ADDED Requirements

### Requirement: The sidebar is handwritten and ordered by use
`wiki/_Sidebar.md` SHALL be written by hand, not generated. It SHALL list Home and Glossary first, then a "User guide" section, then a "Contributor docs" section with the subsections Set up, Backend, Frontend and Services, then Ideas. Within a section the pages SHALL follow the order a reader needs them, not alphabetical order. Link text SHALL NOT repeat the section name as a prefix.

#### Scenario: A reader scans the sidebar
- **WHEN** a reader opens any wiki page
- **THEN** the sidebar shows Home and Glossary first, the user-guide pages next, and the contributor pages grouped under Set up, Backend, Frontend and Services

#### Scenario: Setup comes first for contributors
- **WHEN** a contributor looks at the "Set up" subsection
- **THEN** "Setup and run" is its first entry

### Requirement: Screen pages are named as pages
The Frontend pages that describe the dashboard's screens SHALL be titled "Overview page", "Sessions page", "Projects page" and "Files page", so that none can be mistaken for an introduction to its section.

#### Scenario: A contributor scans the Frontend section
- **WHEN** a contributor reads the Frontend entries in the sidebar
- **THEN** the screen pages read "Overview page", "Sessions page", "Projects page" and "Files page"
