## Why

The Live sessions view and the toasts are only useful while something is open or firing, and day to
day the Ledger is never started: the backend, frontend and Docker gateway all have to be launched by
hand. The user wants the live session list, with each session's context size, always visible on the
desktop, brought up with one click (or at logon) without starting the frontend or Docker.

## What Changes

- Add a `widget/` Electron app: a small, frameless, always-on-top window that lists live sessions from
  `GET /api/live`, each with its context size (the server's own `context.label`), growth marker and a
  `pending` badge when a prompt is waiting. It has its own small renderer and imports nothing from `web/`.
- The widget is read-only. It does not render or answer prompts. Clicking a session opens or focuses
  that repo's editor window (the same `open-repo` action the toasts use); a separate "Open Ledger"
  action starts the frontend on demand and opens the dashboard in the browser.
- Add a tray icon (open Ledger, start backend, quit) and a remembered window position.
- Add `Start-Widget.ps1` (backend if not already up, hidden, then the widget; single instance),
  a desktop shortcut installer, and an optional logon autostart. Neither starts the frontend or the
  gateway container.
- The repo gains a sixth top-level folder, `widget/`; the "exactly five folders" rule in
  `CLAUDE.md` and the layout docs is updated to match.

## Capabilities

### New Capabilities
- `desktop-widget`: the floating always-on-top live-sessions widget, its context-size and pending
  display, its click and tray actions, and the one-click/logon startup that brings up only the
  backend and the widget.

### Modified Capabilities
<!-- None: no existing requirement changes. The folder-count wording lives in docs, not specs. -->


## Impact

- New: `widget/` (Electron main process, renderer, its tests, `package.json`), `Start-Widget.ps1`
  and shortcut/autostart installer scripts.
- One small API addition: `/api/live` sessions gain `git_branch` (from `ledger.db`; empty when unknown).
  `/api/live` already returns `context` (`size`, `growth`, `history`, `label`) and
  `pending_decision`; `POST /api/sessions/{id}/open-repo` already exists. Localhost needs no token;
  non-GET calls send `X-Requested-With: ledger`.
- Docs: `CLAUDE.md`, `wiki/Repository-Layout.md`, `wiki/Coding-Standards.md` (folder counts), a new
  wiki page for the widget, `wiki/Home.md` and `wiki/_Sidebar.md`. `api/check_docs.py` already
  discovers top-level entries dynamically.
- New dependency: Electron (in `widget/` only).
