# jois-stage Specification

## Purpose

Defines `/jois:stage`, the command that clears a messy working tree one concern at a time, each commit confirmed with a word.

## Requirements

### Requirement: Stage works through a dirty tree one concern at a time
`/jois:stage` SHALL read `git status` and the diffs, choose the first concern under the
commit-hygiene rule, stage exactly that concern by explicit path and present it. It SHALL NOT
depend on an OpenSpec change. Deletions, renames or moves, regenerated or binary assets, a lockfile
and a format-only change SHALL each be their own concern, and a hand-written change over about 200
lines or 5 files, or spanning more than one layer, SHALL be split before it is presented.

#### Scenario: Mixed tree is split
- **WHEN** the working tree holds a bug fix and a 40-file deletion
- **THEN** the command SHALL present them as two separate commits, one after the other

#### Scenario: Works without a change
- **WHEN** no OpenSpec change exists
- **THEN** the command SHALL still run

### Requirement: Presentation ends the turn with a confirmation word
After staging a concern, `/jois:stage` SHALL print as plain text the staged file summary and the
proposed commit message, name a common confirmation word that differs from the word in its previous
prompt, state "reply with <word> to commit", and end its turn. It SHALL NOT call a question tool
and SHALL NOT run `git commit` in that turn.

#### Scenario: Turn ends after staging
- **WHEN** a concern has been staged
- **THEN** the command SHALL print the summary, the message and the word, and make no further tool call

#### Scenario: Wrong reply does not commit
- **WHEN** the user replies "looks good"
- **THEN** the command SHALL NOT commit and SHALL restate the current word

### Requirement: The typed word commits and the loop continues
When the user's next message is the word from the most recent prompt, `/jois:stage` SHALL commit
exactly the staged change, with the attribution line given for the session, and SHALL then stage
and present the next concern. It SHALL repeat until `git status` shows a clean working tree, and
then report the commits made. If the user asks for changes instead, it SHALL restage, present again
and name a new word.

#### Scenario: Loop reaches a clean tree
- **WHEN** the user confirms the last of three concerns
- **THEN** the command SHALL commit it, find the tree clean and report the three commits

#### Scenario: Changes requested
- **WHEN** the user answers a prompt with a request to change the message
- **THEN** the command SHALL revise, restage, present again with a different word and end its turn

### Requirement: Unsafe and partial content is handled explicitly
`/jois:stage` SHALL NOT stage untracked or modified files that look unsafe (secret files such as
`.env` or `*.pem`, and build output), SHALL list each by name as skipped, and SHALL NOT count them
against a clean tree. When one file mixes two concerns it SHALL split it by applying a prepared
patch to the index, since interactive staging does not work, or else report the file and ask the
user to split the edit. It SHALL NOT commit while the build or tests fail unless the commit is the
fix, and it SHALL NOT use `git add .`, `git add -A` or `git commit -a`.

#### Scenario: Secret file is skipped
- **WHEN** an untracked `.env` is in the tree
- **THEN** the command SHALL leave it unstaged and name it in its report

#### Scenario: Pre-staged changes
- **WHEN** the index already holds staged changes at the start
- **THEN** the command SHALL include them in its concern analysis and say so, not silently commit them as one block

#### Scenario: Red build
- **WHEN** the build fails and the staged concern is not the fix
- **THEN** the command SHALL NOT commit and SHALL report the failure
