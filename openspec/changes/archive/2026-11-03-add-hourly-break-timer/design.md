# Design

## Context

See proposal.md for why. Facts about the current code that shape the approach:

- **Widget main process** (`widget/src/main/`) owns windows, the AFK flag file and all backend calls. The renderer is sandboxed with a strict CSP and reaches the main process only through a narrow preload bridge (`widget/src/preload/`). Channel names live in `widget/src/shared/ipc.ts` and are repeated in the preload, with `tests/ipc.test.ts` keeping them in step.
- **AFK state** is read from a file on every 2 second poll (`pollLiveAndAfk` in `afk.ts`) and pushed to the renderer. A missing chime install reads as off, so the timer works without the chime hooks.
- **Settings numbers** (`max_projects`, `afk_minutes`) follow one path: validator in `api/app/core/widget_settings.py`, store key in `settings_store.py`, service, router, schema, then a hook in `web/src/api/queries.ts` and a field on `SettingsPage.tsx`. The widget reads them from `GET /api/settings` over loopback through `api.ts`.
- **Local-only routes** check `is_local` in the router. `api/app/deps.py` already defines `REPO_ROOT`.
- **Tooltip window** is unfocusable and mouse-transparent, so it cannot be reused for a clickable window. `app.on('window-all-closed')` quits the widget, which stays safe because the list window is always open.
- **Layout rule:** `CLAUDE.md` allows exactly six top-level folders, so workouts go under `widget/`.
- **Build:** the renderer is plain HTML, CSS and `tsc` output; `widget/scripts/copy-static.mjs` copies static files into `dist/ui/renderer/`.

## Goals / Non-Goals

**Goals:**
- Keep the timer a pure, fake-clock-testable function, separate from windows and files.
- Give the break window exactly the files of the chosen workout and nothing else.
- Follow the existing settings and bridge patterns so the change reads like its neighbours.

**Non-Goals:**
- A folder picker or a configurable workouts path.
- Pausing on system idle time, or snoozing a break.
- Video starters, or a video editor or trimmer.
- Reading the workouts folder from the backend, or listing workouts in the dashboard.

## Decisions

### Folder layout and gitignore
`widget/workouts/starter/` is committed and `widget/workouts/mine/` is ignored by one `.gitignore` line. A workout is a video file directly in a folder, or a subfolder of images with `workout.yaml`. One discovery function takes both folder paths as arguments, so tests pass throwaway folders.
- *Alternative: one `widget/workouts/` folder, ignoring everything but starters.* Rejected: an ignore rule with exceptions is easy to get wrong and could let a personal file be committed.
- *Alternative: `api/.ledger/workouts/`.* Rejected: the widget owns this feature, and `.ledger/` is the backend's data folder.

### The folder path is fixed, shared by name
The widget builds the path from `repoRoot` in `config.ts`, and the backend from `REPO_ROOT`. Both use the same relative string `widget/workouts/mine`. A test on each side pins that string, and the widget test also checks `.gitignore` lists it, so the three cannot drift unnoticed.
- *Alternative: the backend sends the path to the widget.* Rejected: the widget must work with the backend down, as the AFK button does.

### Timer is a pure state object with an injected clock
`BreakTimer` takes `now()` and the break length, and exposes `tick(afkOn)`, `reset()` and `due`. Each tick adds `min(now - lastTick, MAX_TICK_MS)` while AFK is off, with `MAX_TICK_MS` about 5 seconds. A PC that sleeps for hours therefore adds one tick, not hours. The break length is passed on every tick, so a new Settings value applies to a count in progress.
- *Alternative: compare wall-clock start time to now.* Rejected: it cannot pause for AFK and counts sleep as work.
- *Alternative: use Electron's `powerMonitor` suspend and resume events.* Rejected: the tick cap needs no Electron and is testable.

The main process ticks once a second and uses the latest AFK state from the existing poll, so AFK lags by up to 2 seconds. It reads the break length every 30 seconds through `api.fetchBreakMinutes()`, which keeps its last value on failure and starts at 60, like `fetchAfkMinutes`.

### Break window is a second BrowserWindow, shown inactive
`breakWindow.ts` creates a focusable, frameless, always-on-top, sandboxed window with its own HTML page and preload, and shows it with `showInactive()` so a stray Space or Enter cannot press Start. It is created when a break is due and destroyed on Close. At most one exists. A break due while one is open is ignored, so closing is what restarts the count.

State lives in the main process: the chosen workout, and whether it is idle, playing or finished. The renderer sends `start`, `skip` and `close`, and receives one `breakState` message. All IPC arguments are type-checked in the handler, like the existing channels.

### Serving files through a custom scheme
`ledger-workout://<root>/<path>` is registered with `protocol.registerSchemesAsPrivileged` (standard, secure, `stream` and `supportFetchAPI`) and handled with `protocol.handle`. `<root>` is `starter` or `mine`. The handler resolves the path against that folder, takes `fs.realpath`, and returns 404 unless the real path is still inside the real root. It then answers with `net.fetch` of the file URL so the video element can seek. The same containment function validates YAML entries at load time, so a bad entry fails the workout early rather than at play time.
- *Alternative: `file://` access or disabling `webSecurity`.* Rejected: it gives the renderer general file access, which the issue forbids.
- *Alternative: read files in main and send bytes over IPC.* Rejected: large videos, and no seeking.

The break page's CSP is `default-src 'none'; script-src 'self'; style-src 'self'; img-src ledger-workout:; media-src ledger-workout:`.

### YAML: parse with `yaml`, validate by hand, generate once
`widget/package.json` gains the `yaml` package, a project-local install. A workout file is `images:` (a list of `{file, seconds}`). Validation is a small hand-written check: `images` is a non-empty list, each `file` is a relative path inside the workout's folder that exists, and `seconds` is a positive number up to 600. Any failure produces a note naming the workout and the reason, and removes it from the pool.

Generation runs only for the personal folder, only when `workout.yaml` does not exist, and uses an exclusive write (`wx` flag) so an existing file can never be replaced, even by a race. Images are sorted with a natural (numeric-aware) file-name order, so `2.png` comes before `10.png`. Default seconds is a named constant, 20. A starter folder with no YAML is a bug caught by a test, not fixed by writing into the repo.

### Countdown in the list window's top bar
The main process owns the timer, so it pushes `{remainingSeconds, paused}` to the list window once a second over one new channel, `break-countdown`, declared in `widget/src/shared/ipc.ts` and repeated in the preload like the other channels. `BreakTimer` gains a read-only `remaining(breakMinutes)` that returns `max(0, length - count)` in seconds. The renderer only draws the value as `m:ss` in a new element that is the first child of `.actions`, before the brightness buttons. It sets a `data-state="paused"` attribute while AFK is on, and a tooltip with the full wording. It shows `0:00` while a break is due or open.
- *Alternative: a second timer in the renderer.* Rejected: it would drift from the main process and could count sleep.

### Random pick
`pickWorkout(pool, previous, random)` takes an injected random function. Skip excludes the current workout when the pool has more than one. It is the only place that touches the pool's randomness, so tests drive it with fixed values.

### Settings and the Open folder button
`break_minutes` follows the `afk_minutes` path end to end: validator (1 to 240, default 60), store key, service, request and response schema, `types.ts`, query hook and a field in a new "Break workouts" block. `POST /api/widget/workouts/open` checks `is_local`, creates the folder, and opens it with `os.startfile` from a small function in `api/app/infra/`, injected in tests so no real Explorer opens. The route takes no input, so there is no path to validate. On failure it returns the path in the error so the page can show it.

### Starter content
Six to eight neck stretches (for example chin tuck, side tilt, ear to shoulder, slow neck roll, look left and right, shoulder shrug), each as four to six SVG frames with a committed `workout.yaml`. SVGs are plain shapes with no scripts, drawn to be readable at about 400 px wide, coloured with CSS variables so they suit light and dark. A test loads every starter folder through the same validator the widget uses.

## Risks / Trade-offs

- **Video seeking through a custom scheme is unverified** → check it in the first task with a throwaway video, and fall back to no seeking if `net.fetch` does not pass range requests.
- **AFK expiring by itself resumes counting while the user is still away** → accepted: Start is required, so a break at an empty desk does nothing harmful. Idle-time pausing is a stated non-goal.
- **The folder path is written twice (TypeScript and Python)** → pinned by one test on each side plus a `.gitignore` check.
- **A new `yaml` dependency** → project-local, one package, and kept to the main process.
- **A second window can steal attention** → it opens inactive and has no sound.
- **Drawn starter stretches may be poor teaching material** → they are labelled as starters, and the personal folder is the place for real videos.
- **`window-all-closed` quits the widget** → safe only while the list window is open; a test asserts closing the break window does not fire it.
