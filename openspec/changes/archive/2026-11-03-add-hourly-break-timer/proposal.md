# Proposal

## Why

Long stretches at the PC strain the neck, and the desktop widget is always on screen while the user works with Claude Code. Making the widget nudge a break once an hour, with a workout to follow along, spares the user from finding one. Using the user's own videos and drawn images keeps the feature free of a third-party site's content, and keeping personal media out of git keeps large files out of the repo. (GitHub issue #59.)

## What Changes

- The widget counts work time and, when the break length is reached, opens a separate break window showing one workout picked at random. Nothing plays until the user presses Start.
- The count runs only while the widget's AFK switch is off. It starts when the widget opens, ignores gaps caused by the PC sleeping, and restarts when the break window is closed.
- The break window has Start, Skip (picks another workout and waits for Start again) and Close buttons.
- A workout is either a video file or a folder of images. An image folder has a YAML file that sets the order and how long each image shows. The widget generates that file the first time it sees the folder, and never overwrites it afterwards.
- Workouts live in two places under `widget/workouts/`, and both feed one random pool:
  - `starter/` is committed: stretches drawn for this repo (SVG frames plus YAML), so the widget is never empty.
  - `mine/` is gitignored: the user's own videos and image folders. The widget creates it if missing.
- The widget serves workout files to the break window through a custom `ledger-workout://` scheme limited to `widget/workouts/`. The renderer gets no general file access, and YAML entries that point outside the folder are rejected.
- An empty pool shows a short note, and a workout with a broken YAML file is skipped with a short note. Neither crashes the widget.
- The Settings page gets a "Break workouts" section with the break length in minutes (1 to 240, default 60), the path of the personal folder, and an Open folder button. The button calls a new local-only backend route that opens the folder in Explorer.
- The widget's list window shows a countdown to the next break at the left end of its top bar, just left of the brightness buttons. It stops while AFK is on and resets when the break window is closed.
- The widget wiki page describes the timer, the countdown, the two folders and the YAML file.

## Capabilities

### New Capabilities

- `break-timer`: the work-time count and its AFK pause, the break window and its buttons, the random pick, the wait for Start, how video and image workouts play, YAML generation and validation, and the starter and personal folders.

### Modified Capabilities

- `dashboard-settings`: a break length setting, and a control that opens the personal workouts folder.
- `desktop-widget`: the widget may read the break length setting, the new break window is a second window that takes focus and clicks, and the list window's top bar shows the time to the next break.

## Impact

- **Widget** (`widget/`): new main-process modules for the timer, workout discovery, YAML handling and file serving; a new break window with its own page and preload; a countdown element in the list window's top bar, fed by one new IPC channel, `break-countdown`; a new `yaml` dependency in `widget/package.json`; new tests; new bridge and IPC channels.
- **Backend** (`api/`): a `break_minutes` widget setting (validator, schema, store, router), and a local-only route that opens the personal folder. The backend learns the folder's path from one shared constant.
- **Frontend** (`web/`): Settings section, query hooks and `types.ts`.
- **Repo**: `.gitignore` gains `widget/workouts/mine/`. The folder sits under `widget/`, so the six top-level folders rule in `CLAUDE.md` still holds.
- **Docs**: `wiki/Widget.md`, `wiki/Backend-API-Routes.md`, and the Settings description in the frontend wiki.
- **Not in scope**: a folder picker, pausing on system idle time, and bundling video starters.
