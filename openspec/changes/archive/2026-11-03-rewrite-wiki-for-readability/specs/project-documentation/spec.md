# Spec Delta

## ADDED Requirements

### Requirement: Wiki pages follow the readability rules
Every wiki page SHALL put its purpose or result first, give each topic its own header nested by hierarchy, and keep each bullet to one idea in one short sentence. A technical term SHALL be defined where it is first used, or link to the glossary page. The rules SHALL be written in `wiki/Coding-Standards.md`.

#### Scenario: A reader opens any page
- **WHEN** a reader opens a wiki page
- **THEN** the first paragraph says what the page covers or what the reader can do with it

#### Scenario: A page uses a term specific to the project
- **WHEN** a page uses a term such as "Remote mode" or "relay hook"
- **THEN** the page defines it in a short phrase at first use, or links to its entry in `wiki/Glossary.md`

#### Scenario: A reader looks up the rules
- **WHEN** a contributor opens "Documentation" in `wiki/Coding-Standards.md`
- **THEN** it lists the readability rules next to the link and size rules

### Requirement: Wiki pages mark what is known, assumed and unchecked
When a wiki page states something that is assumed or has not been checked against the code, it SHALL mark it as such, apart from what is known. A page SHALL NOT present an unchecked statement as fact.

#### Scenario: A page records an unverified behavior
- **WHEN** a page describes behavior nobody has confirmed in the running app
- **THEN** the statement is labeled "assumed" or "unchecked"

### Requirement: The wiki has a user guide
The wiki SHALL include a user guide made of flat `Guide-*.md` pages, one per task a person does with the dashboard. The guide SHALL cover starting and signing in, the Overview, Live sessions, All sessions, Projects, Files, Settings, Remote access from another device, the desktop widget, and notifications. `Home.md` and `_Sidebar.md` SHALL list the guide pages under a "User guide" heading.

#### Scenario: A person wants to use the dashboard
- **WHEN** a person opens `Home.md`
- **THEN** they see a "User guide" section linking to each guide page, before any contributor-facing section

#### Scenario: A guide page is added without a link
- **WHEN** a `Guide-*.md` page is not linked from `_Sidebar.md`
- **THEN** the docs check fails and names the orphan page

### Requirement: Guide pages describe steps a person can follow
Each guide page SHALL open with what the person can do, then give numbered steps in the order they are taken, using the names shown on screen. A guide page SHALL link to the requirements page or contributor page for detail, and SHALL NOT restate requirements.

#### Scenario: A person follows a guide page
- **WHEN** a person follows the numbered steps on a guide page
- **THEN** each step names a control or page as it appears on screen, not a component or file name

#### Scenario: A guide page needs a technical detail
- **WHEN** a guide page would need to explain how the code works
- **THEN** it links to the contributor page that explains it instead
