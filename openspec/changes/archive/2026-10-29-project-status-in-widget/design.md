## Context

See proposal.md for motivation. Relevant current state:

- `GET /api/projects/repos` already returns `{path, host, url, issues, prs}` per project, cached on
  the server for 5 minutes (60 seconds after an incomplete lookup). It takes no parameters and runs
  `git` and `gh` only in known project folders. It has no project name; the Projects page derives it.
- The widget talks to the backend over `127.0.0.1` with no token, which the backend treats as local,
  so `/api/settings` (local-only) is readable from it.
- The widget's tooltip is one window (`tooltipWindow.ts`) driven by `RemoteTooltip`, triggered by
  the Ledger button's hover. `TooltipContent` is a union the main process builds and the page only
  renders.
- `settings_store.save_worktree_folders` rewrites `settings.json` with only `worktree_folders`, and
  the settings save path reconciles history and rescans the snapshot.
- The only way to drop the server's repo cache is `POST /api/refresh`, which also rescans everything.

## Goals / Non-Goals

**Goals:**
- Hover shows rows instantly, never waiting on `gh`.
- Reuse the existing tooltip window, placement and opaque styling.
- One new setting, editable in the dashboard, without side effects on worktree attribution.

**Non-Goals:**
- Forcing fresher data than the server cache allows; the widget never calls `/api/refresh`.
- A settings UI or any write path in the widget.
- Scrolling or interaction inside the tooltip (it ignores the mouse).
- Changing `/api/projects/repos`.

## Decisions

**Two controllers, one window.** A new `ProjectsTooltip` controller (own hover, own poll) sits beside
`RemoteTooltip`; `TooltipContent` gains `{kind: 'projects', rows, more}`, with loading and failure
text using the existing `message` kind. Both controllers present into the one window. The Remote and
Ledger buttons are never hovered at once, but the Remote tooltip can auto-show while the Ledger is
hovered, so a hide from one must not hide the other's content: the window hides only when neither
controller has content. Alternative: a second window per tooltip. Rejected: it doubles the window
setup (focusless, click-through, theme) for no gain.

**Hover moves by a new IPC channel.** The renderer sends `remoteHover` for the Remote button and keeps
`ledgerHover` for the Ledger button. Main routes `remoteHover` to `RemoteTooltip.setHover` and
`ledgerHover` to the projects controller. Alternative: one channel with a payload naming the button.
Rejected: the existing channel is typed per purpose.

**Read-through cache in the widget, refetch on hover.** The controller keeps the last rows and the
last cap. It fetches at startup, every 60 seconds (the server's failure TTL, so a `gh` sign-in shows
within a minute, and almost always a server cache hit), and on each hover. A hover renders from the
cache immediately and starts a refetch; if the tooltip is still open when it lands, the content-key
comparison in `refresh` redraws only if something changed. A failed read keeps the last rows. The
poller reuses `startPoller` (which never overlaps polls).

**Filtering, ordering and the cap happen in the widget.** The backend returns every project; the
widget keeps `host === 'GitHub'`, sorts by `(issues ?? 0) + (prs ?? 0)` descending with unavailable
counts last and a stable sort for ties, names each row from the path's last segment, and slices to
the cap, reporting the remainder as "+N more". Alternative: a server endpoint that does this.
Rejected: no backend change is needed, and the web page needs the unfiltered list.

**The cap lives in the settings file, saved by its own path.** `settings_store` becomes
read-modify-write for the whole file, with a loader and saver per key, so saving one key never drops
another. `settings_service.save_settings` takes both parts, validates every one before saving any (a bad
number never leaves the folders half-saved), and applies the number with no history reconcile or
snapshot rescan, so a display preference is cheap and cannot affect attribution. `PUT /api/settings` takes both fields optional and applies whichever are present;
`GET` returns `{worktree_folders, widget: {max_projects}}`. Validation: an integer from 1 to 10 (a
bool is not an integer), 400 otherwise; a stored value that is missing or out of range reads as 5.
Alternative: a separate `/api/settings/widget` route. Rejected: the page's single `useSaveSettings`
mutation and cached `Settings` object fit one route, and locality is enforced in one place.

**The widget reads the cap with each repo read.** It calls `/api/settings` alongside
`/api/projects/repos`, and falls back to 5 if that call fails, so a settings problem never hides the
list. The widget keeps 5 as a constant default; the backend value wins when readable.

## Risks / Trade-offs

- **Hover-triggered reads hit `gh` after a cache expiry** -> the server's cache and 4-worker pool
  bound the cost; the widget never overlaps reads, and the hover itself never waits.
- **Data can be up to the server TTL (5 minutes) stale** -> accepted; a manual refresh in the browser
  drops the cache and the widget picks it up on its next read.
- **Moving the QR tooltip to the Remote button changes a habit** -> noted as breaking in the proposal;
  the auto-show on ready still pops it up without hovering.
- **Two controllers share one window** -> hide only when neither has content, covered by a test.
- **Clobbering `settings.json`** -> read-modify-write plus a test that saving each key leaves the
  other intact.

## Migration Plan

No data migration: a settings file without the new key reads as 5. Rollback is a revert; an extra
key left in `settings.json` is ignored by the old code and dropped the next time it saves folders.
