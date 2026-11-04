# Guide: Settings

Change how the dashboard groups worktree sessions and how the desktop widget behaves.
The Settings page appears only in a browser on the PC that runs the Ledger. On any other device it is hidden and the address sends you home.

## Open the page

1. Open the dashboard on the PC that runs the Ledger.
2. Click **Settings** in the navigation.

## Count worktree sessions under their repository

A worktree is a separate working copy of one repository, kept in a folder inside it, such as `.trees`.
A session started in `<repo>/<folder>/<name>` then counts toward its repository instead of showing up as a project of its own.

1. Find the **Worktree folders** list.
2. Read the entry marked **Built in**. It always stays and has no remove button.
3. Type a folder name in **Add a folder**, for example `.trees`.
4. Click **Add**.
5. Read "Saving and re-filing sessions…" while it saves. The change applies at once.
6. To undo it, click **Remove** beside the folder.
7. If the folder is not accepted, a message says why.

## Choose how many projects the widget lists

1. Find the **Desktop widget** section.
2. Enter a number in **Projects shown (1 to 10)**.
3. Click **Save**.
4. Wait up to a minute for the widget to pick it up.

## Choose how long AFK stays on

AFK is a widget switch that makes the chime sounds play even while you are at the keyboard. See [Notifications](Notifications.md).

1. Enter a number in **AFK minutes (1 to 240)**.
2. Click **Save**. Its button is named "Save AFK minutes".
3. Know that a new number applies the next time you turn AFK on, not to one already on.

## Choose the break length

1. Find the **Break workouts** section.
2. Enter a number in **Break minutes (1 to 240)**.
3. Click **Save**. Its button is named "Save break minutes".
4. Wait about 30 seconds for the widget to pick it up. See [Desktop widget](Widget.md).

## Add your own workouts

1. In **Break workouts**, find the folder path `widget/workouts/mine`. <!-- docs-check: ignore -->
   It is not in a fresh checkout until the widget creates it.
2. Click **Open folder**. It opens in your file manager and is created first if it is missing.
3. Put your own workout videos, or folders of images, in it. They join the starter workouts.
4. If it fails, a message appears.

## Checked and unchecked

- Checked: every header, label and button above against `SettingsPage.tsx`, and the default and range of each number against `openspec/specs/dashboard-settings/spec.md`.
- Unchecked: the page was not run in a browser, so no saved value was seen reaching the widget.

## More detail

- [Frontend: Shell and theme](../Frontend/Shell-And-Theme.md) covers how the navigation hides this page.
- [Widget](../Services/Widget.md) explains how the widget reads these settings.
- `openspec/specs/dashboard-settings/spec.md` holds the requirements, including defaults.
