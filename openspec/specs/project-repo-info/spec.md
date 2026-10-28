# project-repo-info Specification

## Purpose

Shows, for each project on the Projects page, where its git repo is hosted and how many issues and pull requests are open there, and links to the repo's web page, so the user does not have to leave the dashboard to find them.

## Requirements

### Requirement: Projects list shows source, issues and pull requests
The Projects list SHALL show, for each project, a Source column naming the host of the project's git remote ("GitHub" for a GitHub remote), an Issues column with the repo's open issue count, and a PRs column with its open pull request count. A value that is unavailable SHALL be shown as `--`.

#### Scenario: GitHub project
- **WHEN** a project's remote is a GitHub repo with 7 open issues and 2 open pull requests
- **THEN** its row shows Source "GitHub", Issues 7 and PRs 2

#### Scenario: Project that is not a git repo
- **WHEN** a project's folder is not a git repo or has no remote
- **THEN** its Source, Issues and PRs cells show `--`

#### Scenario: Non-GitHub remote
- **WHEN** a project's remote is hosted somewhere other than GitHub
- **THEN** its Source cell shows a neutral host label, and its Issues and PRs cells show `--`

### Requirement: Counts never block or break the Projects page
The Projects list SHALL render without waiting for the issue and pull request counts, and SHALL show `--` for them until they arrive. When the counts cannot be read, whether the GitHub CLI is missing, signed out, offline or rate-limited, the affected cells SHALL show `--` and nothing else on the page SHALL change. Counts SHALL be cached for a few minutes so that reloading the page does not query the host again.

#### Scenario: Table renders before counts
- **WHEN** the user opens the Projects page
- **THEN** every project row is shown immediately, with `--` in Issues and PRs until the counts load

#### Scenario: GitHub CLI unavailable
- **WHEN** the GitHub CLI is not installed or not signed in on the machine running the app
- **THEN** the Issues and PRs cells show `--`, and the Source cell and links still work

#### Scenario: Recent counts are reused
- **WHEN** the user reloads the Projects page shortly after the counts were read
- **THEN** the same counts are shown without a new query to the host

### Requirement: Source and Open project link to the remote's web page
The Source cell SHALL link to the web page of the project's git remote, and the selected project's panel SHALL offer an "Open project" control, placed to the left of "Delete project", that opens the same page in a new tab. A project without a resolvable remote SHALL have no link and no "Open project" control. Unlike "Delete project", the control SHALL be shown on every device, local or remote.

#### Scenario: Source opens the repo
- **WHEN** the user activates the Source cell of a project whose remote is `git@github.com:acme/app.git`
- **THEN** `https://github.com/acme/app` opens in a new tab

#### Scenario: Open project opens the repo
- **WHEN** the user activates "Open project" in a project's panel
- **THEN** the same remote web page opens in a new tab

#### Scenario: Open project sits beside Delete
- **WHEN** a project's panel is shown on the machine running the app
- **THEN** "Open project" appears immediately to the left of "Delete project"

#### Scenario: No remote
- **WHEN** a project has no resolvable remote
- **THEN** its panel has no "Open project" control and its Source cell is not a link

#### Scenario: Remote device
- **WHEN** the Projects page is open on a device that isn't the machine running the app
- **THEN** "Open project" and the Source link are still shown, and "Delete project" is not

### Requirement: Repo lookups only use known project paths
The app SHALL run git and the GitHub CLI only against project folders recorded in Claude Code's configuration, and SHALL NOT use a path supplied by a request for them.

#### Scenario: Unknown path
- **WHEN** a request names a path that is not one of the known projects
- **THEN** no git or GitHub CLI command is run for it
