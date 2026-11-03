# Widget

This page explains how the desktop widget in `widget/` is built: its window, how it starts, what it controls and how each feature works. Read it before changing the widget.

> Requirements live in `openspec/specs/desktop-widget/spec.md`. This page describes how the code meets them, not what it must do.

## What the widget is

`widget/` is a small Electron app (a desktop app built on web technology). Its window is frameless and always on top. It lists the live Claude Code sessions with each one's context size, so the Ledger is useful without opening it. A live session is defined in the [Glossary](Glossary.md#live-session).

It only reads sessions, apart from three switches. It is Windows-only, like `hooks/`. It has its own `package.json` and imports nothing from `web/`. It is the only part of the repo that is not a service, a hook or a skill.

### What it writes

- The Remote mode switch, through the backend.
- The per-row auto-approve button, through the backend.
- The AFK button, a local file write described under [AFK button](#afk-button).

## How it works

Loopback means the machine's own address, `127.0.0.1`. IPC means messages between Electron's two processes. The preload is a small script that gives the renderer a narrow, safe set of functions.

```text
Electron main process                      renderer (sandboxed)
  poller --GET /api/live--> backend          plain TS + HTML + CSS
  supervisor (hidden backend/frontend)       rows, pending tint, offline state
  tray, window, saved bounds   --IPC-->      window.widget (narrow preload API)
```

### Polling

The main process polls `GET /api/live` on `127.0.0.1:<backend port>` every 2 s. The code is in `widget/src/main/poller.ts` and `api.ts`. The timeout is 3 s.

Any failure becomes the offline state and clears the rows. Failures are: refused, timeout, non-200, malformed body. Stale data is therefore never shown.

Loopback needs no token, and the widget stores none. The widget exposes no port of its own.

### The renderer never calls the API

The backend has no CORS middleware. The renderer runs with `contextIsolation`, `sandbox`, no `nodeIntegration` and a strict CSP.

It gets state and sends clicks through the preload bridge, `widget/src/preload/index.ts`. The channel names live in `widget/src/shared/ipc.ts`. The sandboxed preload cannot import them, so a test keeps both in step.

### What a row shows

#### Context text

A row shows `context.label` verbatim, for example `394k ▲ +2.1k ▁▂▃▅`. That string is built by `formatting.format_context` for the Live table and the toast. A row shows `--` when `context` is null. The widget has no token formatter of its own.

#### Pending tint

A row gets the `pending` class (warm background) when `pending_decision` is set. There is no badge text. The prompt itself is never read or shown. No individual prompt can be approved here; answer in the terminal or the Ledger.

#### Compact dot

The first thing inside `.row-open` is a `compact-dot`. It is coloured by `compact.state`: green `ok`, amber `should`, red `needs`. It is drawn hollow while `status` is `idle`. A session with no grade gets an invisible placeholder, so names stay aligned. It stays fully opaque (see Status tint).

#### Status tint

A row's tint follows its `status`. A pending decision always wins. The rest follow this list:

- `idle` gets the `done` class (green background).
- `busy`, `unknown` or an empty status keeps the default look.
- Any other status gets the `error` class (red background).

The rule is `rowTint` in `widget/src/renderer/view.ts`. The tint colours are mixed with `--bg-alpha`, so they follow the transparency buttons like the window background. Text and the compact dot stay opaque.

#### Branch

`/api/live` items carry `git_branch`. It is looked up from `ledger.db` in `LiveSnapshot`. It is empty when unknown.

### What a row does

#### Auto-approve button

Each row gets a small "Auto" button at its right end once `/api/meta.relay_hook_seen` is true. The widget reads that value right after each `/api/live` poll. Anything unreadable counts as not seen. The button is outlined when off and filled when on.

A row is a `div.row` holding two sibling buttons: `.row-open` (the repo window) and `.auto-approve`. They are siblings because a button cannot nest in a button. Pressing `.auto-approve` never opens the repo.

It calls `POST /api/sessions/{id}/auto-approve` through the `setAutoApprove` bridge method. The state follows the next poll. A refusal shows a brief note.

#### Row click

A click calls `POST /api/sessions/{id}/open-repo`, the toast-click action. A 404 shows a brief "Session ended" note and refreshes the list.

## Starting it

### The start script

`widget/Start-Widget.ps1` uses the ports `Start-Ledger.ps1` chose and saved. The backend's port follows the same rules: parameter, root `.env`, saved port, first free one in 8501-8599. The frontend's port comes from parameter, `.env`, saved port, else 8502. The frontend port is never scanned, because this script does not start the frontend.

Before launching, it checks the backend's venv, the widget's packages and the Electron binary against their requirements and lock files. It installs whatever is missing or stale. An empty `node_modules` or a missing `electron.exe` is repaired, not trusted because the folder exists. It stops with an error if that fails. It rebuilds when the sources are newer than `dist/`, then launches Electron.

`Start-Widget.vbs` runs it with no console window. That is why the checks live here rather than only in `Start-Ledger.ps1`.

```powershell
.\widget\Start-Widget.ps1                           # widget + the backend it needs
.\Install-Ledger.ps1                                # offers the shortcut and the sign-in autostart
.\widget\Install-WidgetShortcut.ps1 -Desktop        # "Ledger Widget" on the desktop (what the installer calls)
.\widget\Install-WidgetShortcut.ps1 -Startup        # also start at sign-in (Startup folder)
.\widget\Uninstall-WidgetShortcut.ps1 [-Startup]    # remove both, or only autostart
```

### Installing

`Install-Ledger.ps1` is the setup route. It asks about the shortcut and, separately, the sign-in autostart. Accepting the shortcut installs the widget's packages first. That way the first launch from the shortcut, which shows no window while it prepares, is not a long silent `npm ci`.

Both shortcut scripts also take `-DesktopPath` and `-StartupPath` to work in other folders. The tests use throwaway folders for these.

### Start-Ledger and Stop-Ledger

`Start-Ledger.ps1` launches the widget too, once the backend answers. `-NoWidget` skips it. It records the widget's PID only when it launched the widget. `Stop-Ledger.ps1` therefore closes that widget and leaves one that was already running.

### The Startup-folder shortcut

It needs no elevation. It shows in Windows' Startup apps list. Removing it leaves the desktop shortcut working.

## Process ownership

The widget's main process starts the backend, in `widget/src/main/supervisor.ts`. The script does not start it. A cold start and the tray's "Start backend" therefore share one code path.

### Backend

If `/api/meta` answers, the backend is adopted and never stopped by the widget. Otherwise the widget spawns `api\.venv\Scripts\python.exe -m app --port <p> --frontend-port <f>`. It is spawned hidden, with `api/` as its working directory.

### Open Ledger

It is in the tray and as the header button. It starts the frontend only if the frontend is not already up. It runs `npm run build` first if `web/dist` is missing or older than `web/src`, `web/index.html` or `web/package.json`. It then runs `npm run preview -- --port <f>` hidden. Then it opens the browser. The widget never starts Docker or the gateway itself.

### Quit

Quit is in the tray. It first turns Remote mode off if the widget started the backend, because otherwise the gateway container would outlive it. It then tree-kills (`taskkill /T /F`) only the processes the widget started.

If the widget is killed instead of quit, its backend can be orphaned. The next launch finds it running and adopts it.

## Remote mode

Remote mode lets other devices on your network use the dashboard; see the [Glossary](Glossary.md#remote-mode).

### The toggle

The header has a Remote mode toggle. The widget only asks: it calls `POST /api/remote-mode`. It reads `remote_mode` from `/api/meta` on its poll. Docker, the frontend and the gateway are the backend's job; see [Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md).

### The tooltip

While Remote mode starts, and when it fails, the Remote button's tooltip shows the step or reason. At `ready`, hovering the Remote button shows a small separate window.

That window is in `widget/src/main/tooltipWindow.ts`. It is frameless, unfocusable, mouse-transparent and sandboxed, with a strict CSP. It shows the sign-in QR, the `https://` address and the time left. The QR is fetched only while hovering and held in memory only. The token is never shown or stored.

`remoteTooltip.ts` holds the message text and placement logic. When a start the widget watched finishes, the tooltip also pops up by itself for a few seconds.

## AFK button

AFK means away from keyboard. The header has an "AFK" switch for the session chimes (see [Hooks](Hooks.md)).

### What it looks like and does

It looks like the Remote button: a small dot and the fixed label "AFK". The dot is green when on and grey when off. On makes the chime hook play even while you are using the PC, until the AFK duration runs out.

### How it switches

It is the widget's first local write. It does not use the backend to switch. The widget writes or deletes one file, `%USERPROFILE%\.claude\hooks\chimeScripts\state\afk.flag`. The file holds the expiry as one `Z`-suffixed UTC time. The hook treats a missing, unreadable or past-due file as no flag.

### Module

`widget/src/main/afk.ts` is the file side. It does four things:

- It reads the flag: off, or on with minutes left.
- It writes the flag from a duration.
- It clears the flag.
- It says whether `Play-ClaudeChime.ps1` is installed.

Each function takes the chime folder as an argument, so tests use throwaway folders. `chimeFolder()` is the one place the widget names the real folder.

### State

Each poll reads the flag beside `/api/live`. It pushes the flag on its own channel, `afkState`. The button therefore follows the file. It shows off within one poll (2 s) of expiry. It works with the backend down.

The button is hidden unless the script is installed. It is also hidden in the collapsed pill.

### Switching on

It uses the `setAfk` bridge channel, like `setAutoApprove`. It reads `widget.afk_minutes` from `GET /api/settings`: 1 to 240, 30 until set. It writes now plus that. If the backend does not answer, it uses the last value read, or 30 if there is none. An AFK already on keeps the time it was given. A failed write shows a brief note.

### Hover text

It says what a click does. While on, it also says the minutes left.

## Projects tooltip

Hovering the Ledger button shows the same kind of window below the widget. It lists the **GitHub** projects with name, source, open issues and open pull requests.

### Where the data comes from

A count that could not be read shows as `--`. It is the Projects page's data, not a second lookup.

The widget reads `GET /api/projects/repos` (see [Backend API routes](Backend-API-Routes.md)). It also reads the `widget.max_projects` setting from `GET /api/settings`. Both reads go over loopback, which counts as a local request, so no token is needed.

The setting is edited on the dashboard's Settings page: 1 to 10, 5 until set. The widget has no settings UI. It falls back to 5 if it cannot read the setting.

### It never waits on `gh`

`ProjectsTooltip` (`widget/src/main/projectsTooltip.ts`) keeps the last read. The widget reads at startup, every 60 s and on each hover. A hover that lands during a read joins it, because `startPoller` never overlaps.

A hover therefore shows the last rows at once. Rows that arrive while it is open replace them in place. The read has its own 30 s timeout, since a cold backend runs `git` and `gh` for every project. A failed read keeps the last rows.

Before the first read, it says "Loading projects...". If none ever succeeded, it says "Could not load the projects".

The widget never calls `/api/refresh`, so it can be as stale as the backend's cache (5 minutes). The Projects page's refresh button drops that cache.

### Which rows

`projectsView` (`widget/src/main/projects.ts`, pure) keeps `host === 'GitHub'`. It orders by open issues plus pull requests. Projects whose counts could not be read go last. Ties keep the backend's order. It names each from the path's last segment. It cuts the list to the setting and reports the rest as "+N more". With no GitHub project it says "No GitHub projects".

### One window, two tooltips

The Remote and Ledger buttons are separate tooltips, using the `remoteHover` and `ledgerHover` IPC messages. They draw into one window through `TooltipSlot` (`widget/src/main/tooltipSlot.ts`). The most recently presented content wins. The window hides only when neither tooltip has content. So the sign-in code appearing on ready and going away does not take a hovered projects list with it.

`tooltipSize` sizes the window. The projects page draws every line 20 px tall, so its height follows the line count. Values are set as text, never markup.

## Break timer

After a stretch of work the widget opens a small break window with one neck workout. Requirements are in the break-timer capability's spec; this section says how the code meets them.

### Timer

`BreakTimer` (`widget/src/main/breakTimer.ts`) is pure, with an injected clock. The main process ticks it once a second. Each tick adds the time since the last one, at most 5 s. It adds only while the AFK switch is off, so sleep adds one tick rather than hours. The AFK state is the latest one the 2 s poll saw, so it can lag by up to 2 s.

The count starts at zero on every launch. It starts at zero again when the break window closes.

The break length is `widget.break_minutes` from `GET /api/settings`: 1 to 240, 60 until set. It is read every 30 seconds (`BREAK_MINUTES_POLL_MS`) through `fetchBreakMinutes`. `fetchBreakMinutes` keeps its last value when the backend does not answer. A new value applies to a count in progress.

### Workout folders

There are two folders: the starter folder and the personal folder. The starter folder is committed and holds the shipped stretches. The personal folder is listed in `.gitignore` and is created when missing. Your own files go in the personal folder.

Both sit under `widget/workouts/`, named `starter` and `mine`. The relative paths are constants in `widget/src/main/workouts.ts`. All workouts from both folders form one pool.

### What a workout is

A workout is a video file directly in a folder, named after the file. Video formats are mp4, webm, m4v, ogv or mov.

Or it is a subfolder of images with a `workout.yaml`, named after the folder. Image formats are png, jpg, gif, svg or webp.

### The YAML file

It has one field, `images`, a non-empty list. Each entry has two fields:

- `file`: a path inside the workout's folder that exists.
- `seconds`: a number above 0 and up to 600.

The images show in list order for their seconds.

If a personal image folder has no YAML file, the widget writes one. That file lists every image in natural file-name order (`2.png` before `10.png`) at 20 s each. It writes with an exclusive flag, so an existing file is never replaced. It never writes into the starter folder.

A workout is left out, with a note, for any of these: an unreadable file, a bad field, a missing image, or an entry that leaves the folder (absolute path, `..` or a link). The note shows in the break window.

### Serving files

The break page gets files only through the `ledger-workout://<root>/<path>` scheme. The code is `widget/src/main/workoutProtocol.ts`; the root is `starter` or `mine`. The handler resolves the real path. It answers 404 unless the path is still inside that folder. It forwards the `Range` header so a video can seek.

The scheme is registered as privileged before the app is ready. Its handler is registered afterwards.

### The break window

The code is `widget/src/main/breakWindow.ts`, with the page `widget/src/renderer/breakWindow.html`. It is a separate, frameless, always-on-top, sandboxed window. It has its own preload and CSP: `default-src 'none'`, images and media only from the workout scheme.

It is focusable so its buttons work. It is shown with `showInactive`, so typing in another window never presses Start. At most one exists. A break that comes due while one is open is ignored.

It shows the workout's name with Start, Skip and Close. Nothing plays until Start. Skip picks a different workout when there is more than one (`pickWorkout`). After Skip it waits for Start again, even during play. Close destroys the window from any state.

With no valid workout, the page shows a note and only Close. A video that cannot play shows a note and keeps Skip and Close.

### State

`BreakController` (`widget/src/main/breakController.ts`) holds the chosen workout. It also holds whether the break is idle, playing or finished. It is independent of Electron: tests pass a fake window.

It sends the page one `breakState` message. The page sends `breakStart`, `breakSkip`, `breakClose` and `breakFinished`. Each is checked in the handler. The page steps images with timers and reports the end.

### Countdown in the top bar

The main process pushes `{remainingSeconds, paused}` to the list window once a second, on the `breakCountdown` channel. It also pushes once when the page finishes loading. The value is `BreakTimer.remaining` for the same break length the tick uses. It is 0 while a break is due or the break window is open. That rule is `breakCountdown` in `widget/src/main/breakTimer.ts`. `paused` is the AFK flag.

The page draws the value as `m:ss` in `#countdown`, the first child of `.actions`. The tooltip reads like "Next break in 42 min 10 s", with "(paused, AFK on)" while paused. `data-state="paused"` dims it.

The collapsed pill hides it by CSS only. Pushes carry on, so the right time shows on expanding. A new break length shows after the next once-a-minute read.

### The list window is untouched

The list window is always open. Closing the break window therefore cannot fire `window-all-closed`. The widget keeps running.

## Window

### Position and size

The last position and size persist to `widget-state.json` under Electron's `userData`. They are clamped onto a visible display on load, in `widget/src/main/state.ts`.

The header's `–` collapses the window to a one-line pill (count and pending count). It expands the window again on a second click.

### Auto height

The renderer measures its header, rows and note after every render. It sends the height over IPC (`setContentHeight`). The main process resizes only the height, keeping position and width. It grows up to 10 rows, then the list scrolls. While collapsed, the report is ignored. Expanding restores the last content height.

### Single instance and tray

A second launch focuses the running widget (`requestSingleInstanceLock`). The window has no taskbar entry. The tray menu has four entries:

- Open Ledger
- Start backend
- Show/Hide widget
- Quit

### Transparency

The header has a small-sun and a big-sun button. They step the background transparency, 10 to 100%, 10% a click; big sun is more opaque. The text does not fade. The value is remembered with the window position.

A transparent frameless window may not be resizable by dragging on Windows.

## Related pages

- [Testing](Testing.md) covers the suites.
- [Hooks](Hooks.md) covers the toast the click action mirrors.
