## Purpose

Turns a code review into a saved, versioned checklist that can be worked through finding by finding across sessions and then archived, and tells the reader when the skills and rules that produced it have since changed.

## ADDED Requirements

### Requirement: Reviews are saved to a file
Every review produced by the `coding-standards` skill SHALL be saved as a Markdown file in a
`reviews/` folder at the root of the reviewed repository, creating the folder if needed. The file
name SHALL be the local date and time the review was made, as `YYYY-MM-DD_HHMM.md`. If that name
already exists, the skill SHALL NOT overwrite it and SHALL add a numeric suffix (`_HHMM-2`). The
skill SHALL tell the user the path when the review is done.

#### Scenario: Review is written to reviews/
- **WHEN** a review completes at 17:07 local time on 2026-10-14
- **THEN** it SHALL exist at `reviews/2026-10-14_1707.md` under the repository root

#### Scenario: Two reviews in the same minute
- **WHEN** `reviews/2026-10-14_1707.md` already exists and another review completes in that minute
- **THEN** the new review SHALL be saved as `reviews/2026-10-14_1707-2.md` and the first SHALL be unchanged

### Requirement: Review metadata
A saved review SHALL begin with YAML frontmatter holding: `reviewed_at` (local date and time),
`scope` (what was reviewed, such as "whole codebase" or a branch), `commit` (the git commit the
line numbers refer to, or `none` outside a git repository), `status` (`open` or `archived`),
`baseline`, `tree_unchanged` and `redactions` (defined by the requirements below), and
`uses`, a list with one entry for every skill and rule applied, each recording its kind, name,
`version`, `last_updated` and content `hash`, the first two taken from its `metadata:` map.

#### Scenario: Metadata records what was used
- **WHEN** a review applied the `coding-standards` skill and the `python.md` and `core-principles.md` rules
- **THEN** `uses` SHALL hold an entry for each of the three, with the version, last-updated date and hash each had at review time

#### Scenario: New review is open
- **WHEN** a review is first saved
- **THEN** its `status` SHALL be `open`

### Requirement: Findings are task-tracking items
The body of a saved review SHALL contain a coverage section stating what was read and what was not,
then a numbered finding block for each finding, then a "what's good" section. Every finding block
SHALL hold: the item number and title; a category that is exactly one of Rule-breaking, Defect,
Structure, Script or Smell; the affected files and lines taken from the review; a symbol anchor
(function, class or component name) for each location; the problem; the proposed fix; and a
checkbox `- [ ]` that is unchecked until the finding is resolved.

#### Scenario: Finding block is complete
- **WHEN** a review reports "open-repo reports success when it fails"
- **THEN** its block SHALL show item number and title, category Defect, the file and line range with the `open_repo` anchor, the problem, the fix, and an unchecked checkbox

#### Scenario: Category is from the fixed set
- **WHEN** any finding is written
- **THEN** its category SHALL be one of Rule-breaking, Defect, Structure, Script or Smell and nothing else

#### Scenario: Unread areas are recorded
- **WHEN** a review skipped the CSS and the widget scripts
- **THEN** the coverage section SHALL name them as not read

### Requirement: Reviews do not change the code
A review SHALL read the code and SHALL NOT modify it. The reading SHALL be done by a
`code-reviewer` agent whose tools are limited to Read, Grep and Glob; the main thread SHALL write
only files under `reviews/`. Before the review starts the skill SHALL record the repository's
`git status --porcelain` and the content of `git diff`, and after it finishes SHALL compare them.
Gitignored files are not part of the comparison. If anything other than the new review file
differs, the skill SHALL report which paths changed and SHALL NOT report the review as clean.
The result SHALL be saved in the metadata as `tree_unchanged: true` or `false`.

#### Scenario: Clean review
- **WHEN** a review completes and only `reviews/2026-10-14_1707.md` is new
- **THEN** the metadata SHALL show `tree_unchanged: true`

#### Scenario: Code was modified
- **WHEN** a tracked source file differs after the review
- **THEN** the skill SHALL name that file, set `tree_unchanged: false` and tell the user the line numbers may not match the recorded commit

#### Scenario: Ignored output is allowed
- **WHEN** the baseline run creates `.pytest_cache/` or `web/dist/`, which are gitignored
- **THEN** the comparison SHALL ignore them and `tree_unchanged` SHALL stay true

#### Scenario: Reviewer cannot write
- **WHEN** the `code-reviewer` agent's tool list is read
- **THEN** it SHALL contain no tool that edits files or runs commands, and the docs check SHALL fail if one is added

### Requirement: Reviews do not read sensitive files
A review SHALL NOT read files that commonly hold secrets, and SHALL NOT write their contents into
a review file. The files given to the reviewer SHALL be the repository's tracked files
(`git ls-files`), so gitignored files such as `.env` are never in scope, minus a sensitive-path
denylist kept in one file shared by every check: `.env` and `.env.*` other than `.env.example`
and `.env.sample`, `*.pem`, `*.key`, `*.pfx`, `*.p12`, `*.keystore`, `id_rsa*`, `credentials*`
and `secrets*`. The `code-reviewer` agent SHALL be instructed never to open a denylisted path.
Because an agent cannot carry its own deny hook, the toolkit README SHALL document a
`permissions.deny` snippet for the same denylist that the user can add to their own
`settings.json`; the installer SHALL NOT write it. Before a review is written, its text SHALL be checked for denylisted paths' contents and
for common secret patterns (private-key headers, long token-like strings, `KEY=value` lines for
secret-named keys), any match SHALL be redacted, and the metadata SHALL record `redactions: N`.
The coverage section SHALL list the skipped sensitive paths by name, never by content.

#### Scenario: Ignored file is out of scope
- **WHEN** the repository has a gitignored `.env`
- **THEN** it SHALL not appear in the file list given to the reviewer

#### Scenario: Tracked sensitive file is excluded
- **WHEN** a tracked file `deploy/server.pem` exists
- **THEN** it SHALL be left out of the file list and named in the coverage section as skipped

#### Scenario: Example file stays in scope
- **WHEN** `.env.example` is tracked
- **THEN** it SHALL remain in the file list

#### Scenario: Documented hard block
- **WHEN** a reader follows the README's sensitive-files section
- **THEN** they SHALL find a `permissions.deny` snippet covering every denylist pattern, stated to be opt-in and applied by the user

#### Scenario: Secret in output is redacted
- **WHEN** the reviewer's findings quote a line such as `API_KEY=abc123…`
- **THEN** the saved review SHALL contain a redaction marker instead of the value and `redactions` SHALL be at least 1

### Requirement: Baseline runs by default
Before reading the code, a review SHALL run the project's test and build commands, found from the
project's own documentation or configuration, on the main thread, and SHALL record each command,
its pass or fail result and a one-line summary in the metadata under `baseline`. A failing command
SHALL NOT stop the review and SHALL be reported as a finding. A baseline command SHALL be skipped
only when no test or build command can be found, in which case the metadata SHALL say
`not run` with the reason.

#### Scenario: Green baseline
- **WHEN** the project's tests and build pass
- **THEN** `baseline` SHALL list each command as passed with its summary

#### Scenario: Failing baseline
- **WHEN** a test command fails
- **THEN** the review SHALL continue, record the command as failed, and include a finding for the failure

#### Scenario: No commands found
- **WHEN** the project documents no test or build command
- **THEN** `baseline` SHALL read `not run` with the reason and the review SHALL proceed

### Requirement: Apply fixes findings one at a time
A `/jois-review:apply` command SHALL take a review file (defaulting to the newest open one in
`reviews/`), select the next finding whose checkbox is unchecked, and resolve only that finding.
It SHALL locate the code by the symbol anchor and the current file contents rather than trusting
line numbers, because earlier fixes move lines. It SHALL run the project's relevant tests and
build, tick the finding's checkbox only when they pass, and then stop for the commit confirmation
required by the commit-hygiene rule before starting another finding. A finding that cannot be
resolved SHALL be left unchecked with a note, never ticked.

#### Scenario: One finding per run
- **WHEN** a review has items 1 to 4 unchecked and apply runs
- **THEN** it SHALL work on item 1 only, tick it on success, and end its turn awaiting commit confirmation

#### Scenario: Lines have moved
- **WHEN** an earlier fix has shifted the code a finding refers to
- **THEN** apply SHALL find it by its symbol anchor and SHALL NOT edit the lines the review originally gave

#### Scenario: Failing tests block ticking
- **WHEN** the tests fail after a fix
- **THEN** the checkbox SHALL stay unchecked and the failure SHALL be reported

#### Scenario: Skipped finding
- **WHEN** the user decides a finding will not be fixed
- **THEN** apply SHALL record `Skipped: <reason>` on that finding and not tick it

### Requirement: Archive closes a finished review
A `/jois-review:archive` command SHALL refuse to archive a review while any finding is both
unchecked and not marked `Skipped: <reason>`, and SHALL list those findings. When every finding is
checked or skipped it SHALL set `status: archived`, record `archived_at`, and move the file to
`reviews/archive/` keeping its name.

#### Scenario: Open findings block archive
- **WHEN** a review still has an unchecked finding with no skip reason
- **THEN** archive SHALL not move the file and SHALL name the open findings

#### Scenario: Completed review is archived
- **WHEN** every finding is checked or skipped with a reason
- **THEN** the file SHALL move to `reviews/archive/` with `status: archived` and an `archived_at` time

### Requirement: Stale reviews are flagged
The `apply` and `archive` commands SHALL compare each `uses` entry's recorded version and hash
with the currently installed skill or rule, and SHALL warn the user, naming each item, when either
differs or the item is no longer installed. A warning SHALL NOT stop the command; the user decides
whether to re-review.

#### Scenario: Rule changed since the review
- **WHEN** `python.md` has a different hash from the one a review recorded
- **THEN** apply SHALL warn that the review used an older `python.md` and name its recorded and current versions

#### Scenario: Nothing changed
- **WHEN** every recorded version and hash matches the installed items
- **THEN** no staleness warning SHALL be shown
