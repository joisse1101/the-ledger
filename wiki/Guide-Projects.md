# Guide: Projects

Browse every project you have used Claude Code in, open a project's charts, jump to its repository and delete a project you no longer want.

## Browse the list

1. Open **Manage Projects** in the top bar (it is labelled Projects on a phone).
2. Read one row per project. The columns include Name, Path, Source, Issues, PRs, Trusted, Last Session, Version, Last Cost, Last Started, Lines +/- and MCP Servers.
3. Read a `--` as "not known". Issues, PRs and Source need `git` and the GitHub CLI signed in on the PC. Without them they stay `--`.
4. Click the host name in the Source column to open the repository's web page in a new tab.
5. If the list is empty it says "No Claude projects found."

## Open a project's charts

1. Click a project's row. Its panel opens directly below the row.
2. Pick a time range with the same buttons as the [Overview](Guide-Overview.md). A range with nothing in it is disabled.
3. Read the charts. They group sessions by worktree. A worktree is a separate working copy of one repository. See [Settings](Guide-Settings.md) to make the Ledger count worktree folders under their repository.
4. Click the row again to close the panel. You can open several panels at once.
5. Copy the page address to reopen the same panels later. Which panels are open is kept in the address.

## Open the repository

1. Open a project's panel.
2. Click **Open project**. It appears only when the project has a remote repository.

## Delete a project

Only a browser on the PC that runs the Ledger shows this button.

1. Open a project's panel.
2. Click **Delete project**.
3. Read the confirmation. It names the project and says it removes the project from `~/.claude.json` and deletes its session transcripts.
4. Click **Delete** to confirm, or **Cancel** to keep everything.
5. Know that deleting cannot be undone.

## Checked and unchecked

- Checked: column headers, button names, the empty message and the confirmation wording against `ProjectsList.tsx`, `ProjectDetailPanel.tsx` and `ProjectsPage.tsx`.
- Checked: the Cancel button's name against `ConfirmDialog.tsx`.
- Unchecked: the page was not clicked through in a running browser.

## More detail

- [Frontend: Projects](Frontend-Projects.md) explains how the page is built.
- `openspec/specs/web-dashboard/spec.md` holds the requirements.
