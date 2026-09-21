## Why

The Ledger only really works on the machine it runs on. Streamlit can be bound to a network interface, but its layout is built from fixed-width `st.columns` rows, CSS hacks over Streamlit's internal test IDs, and modal dialogs, none of which adapt to a phone-sized screen. The Live sessions table is the thing you most want to glance at from a phone while Claude works, and it is the hardest part to make responsive there. Exposing the app on the network also raises a problem Streamlit has no answer for: it can delete sessions and projects and shows transcript prompts, with no authentication. Moving to a React front end over a small HTTP API fixes both: real responsive layout, and a place to put access control.

## What Changes

- Replace the Streamlit UI with a React + TypeScript single-page app (Vite) using the same three pages: Overview, Sessions (Live + All), Projects.
- Add a FastAPI backend that exposes the existing Python data layer (`claude_db`, `claude_sessions`, `claude_transcripts`, `claude_projects`, `claude_context`) as a JSON API and serves the built React bundle, so it is still one process on one port (8501).
- The UI adapts to screen size: tables become stacked cards on narrow screens, the nav bar becomes a compact bar with a bottom tab bar on phones, the session detail dialog becomes a full-screen sheet, and the Overview grids collapse to one or two columns. No horizontal page scroll at 360px wide.
- Add an opt-in LAN mode (`--lan`, binds `0.0.0.0`) with **shared-token auth for non-localhost clients**. Localhost stays open. The token is persisted so a phone stays signed in across restarts, and the server prints a one-time URL (with a terminal QR code) to open on the phone.
- Move the Overview aggregation (time-range filter, per-project totals, hourly activity) and the All-table search/filter/sort out of `views/` into plain Python modules behind the API, keeping their existing behavior and tests.
- The live-session polling (2s), the manual refresh control, and the 10-minute background refresh keep working. Auto-refresh moves from a per-browser-tab Streamlit fragment to a server-side timer, and the client pauses polling while its tab is hidden.
- Dark mode becomes per device (follows the OS by default, toggle stored in the browser) instead of the process-wide `theme.base` hack.
- **BREAKING**: `streamlit run app.py` no longer exists. The app starts with `python server.py` (after a one-time `npm run build`). `app.py`, `views/`, `.streamlit/`, and the `streamlit`/`pandas` runtime dependencies are removed. Node.js is now needed to build the front end.
- **BREAKING**: The SQLite snapshot moves from `.streamlit/ledger.db` to `.ledger/ledger.db`, since `.streamlit/` goes away. It is still a derived cache that is wiped and rebuilt on start.
- Delete of a live session is now enforced by the server (409), not just hidden in the UI.

## Capabilities

### New Capabilities
- `web-dashboard`: the Overview, Sessions (Live and All), and Projects pages as a web app: what each shows, search/filter/sort on the All table, the session detail view and delete flows, refresh behavior, and per-device theme. Captures the existing Streamlit behavior as requirements so parity is checkable.
- `responsive-layout`: how the UI adapts across phone, tablet, and desktop widths (navigation, tables to cards, detail sheet, Overview grids, touch targets, no horizontal scroll).
- `network-access`: serving the app to other devices on the network, including the opt-in LAN bind, shared-token auth for non-localhost clients, host validation, request validation on identifiers that reach the filesystem, and startup output for opening it on a phone.

### Modified Capabilities
- `live-context-gauge`: the Context value is no longer necessarily a table *column* (it is a labelled field in the phone card layout), and the detail view is opened from a row *or card*. Behavior of the numbers themselves is unchanged.

## Impact

- **Removed**: `app.py`, `views/` (all modules), `.streamlit/config.toml`, `tests/test_app.py`, `tests/test_views.py` (their pure-logic cases are ported), and the `streamlit` dependency. `pandas` is dropped if nothing else needs it.
- **New**: `server.py` (FastAPI app + CLI), a small Python package/modules for API-facing aggregation (`overview_stats`, transcript query), `web/` (Vite React app with its own `package.json`), `.ledger/` (gitignored: `ledger.db`, `token`).
- **Unchanged**: `claude_context.py`, `claude_sessions.py`, `claude_projects.py`, `claude_transcripts.py`, and the parsing in `claude_db.py` (apart from `db_path()`), plus `hooks/`.
- **Dependencies**: adds `fastapi`, `uvicorn`, `qrcode` (Python); `react`, `vite`, `typescript`, `vega-embed`/`vega-lite`, a data-fetching helper (Python dev: `httpx` for `TestClient`). Requires Node.js to build.
- **Docs**: `CLAUDE.md` (architecture section rewritten), `README.md` (setup/run, Windows Firewall note, LAN and token instructions).
- **Security surface**: the app becomes reachable by other devices when `--lan` is used. Traffic is plain HTTP, so the token is only as safe as the network. This is stated in the docs and the design, not solved with TLS in this change.
