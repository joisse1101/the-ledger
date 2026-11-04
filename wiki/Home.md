# The Ledger

The Ledger is a dashboard for your local Claude Code sessions and projects.
Use these pages to run it, to learn each screen, or to change the code.

It shows Overview, Sessions (Live and All), and Projects. It is an API-only FastAPI backend (`api/`) plus a React + Vite frontend (`web/`). Another device on the same network can read it through a gateway, behind a shared access token. Terms such as "gateway" and "access token" are explained in the [Glossary](Glossary.md).

> **Edit these pages in the repo (`wiki/`), not on the GitHub wiki.** The wiki is a one-way mirror
> published on every push to `main`; edits made in the browser are overwritten.

## User guide

Start here to use the dashboard. Each page gives numbered steps for one task.

- [Getting started](User-Guide/Getting-Started.md): install, start, open the dashboard, sign in
- [Overview](User-Guide/Overview.md): counts, time, cost, tokens and working hours across projects
- [Live sessions](User-Guide/Live-Sessions.md): see running sessions, answer a prompt, auto-approve, compact badges
- [All sessions](User-Guide/All-Sessions.md): search, filter, sort, open and delete past sessions
- [Projects](User-Guide/Projects.md): browse projects, open their charts, delete one
- [Files](User-Guide/Files.md): move files between the PC and another device
- [Settings](User-Guide/Settings.md): worktree grouping and widget behavior
- [Remote access](User-Guide/Remote-Access.md): open the dashboard from a phone or another computer
- [Desktop widget](User-Guide/Widget.md): floating live-sessions window and break timer
- [Notifications](User-Guide/Notifications.md): toasts and chimes when a session finishes or needs you

## Contributor pages

Read these to change the code. Requirements live in `openspec/specs/`, not here.
Docs conventions are in [Coding standards](Contributing/Coding-Standards.md).

### Getting started

- [Setup and run](Contributing/Setup-And-Run.md): install, start, ports, history backup task
- [Testing](Contributing/Testing.md): running the Python and frontend suites
- [Repository layout](Contributing/Repository-Layout.md): folders, gitignored state, OpenSpec
- [Coding standards](Contributing/Coding-Standards.md): what "human-understandable" means here
- [Glossary](Glossary.md): plain-English meanings of terms used across the pages

### Backend

- [Data layer](Backend/Data-Layer.md): SQLite snapshot, projects, transcripts, live sessions, context
- [History store](Backend/History-Store.md): durable history and the backup script
- [API routes](Backend/API-Routes.md): the route table and server startup
- [Security](Backend/Security.md): access token, local vs. remote, CSRF header
- [Live sessions and prompts](Backend/Live-Sessions-And-Prompts.md): live snapshot, pending decisions, Remote mode
- [Overview and queries](Backend/Stats-And-Queries.md): aggregation and filter/sort modules

### Frontend

- [API layer](Frontend/Api-Layer.md): stack, sign-in token, fetch client, query hooks
- [Shell and theme](Frontend/Shell-And-Theme.md): app shell, viewport classes, theme tokens, local-only Settings page
- [Sessions](Frontend/Sessions-Page.md): Live and All pages, dialogs, prompts
- [Overview](Frontend/Overview-Page.md): charts and summary stats
- [Projects](Frontend/Projects-Page.md): project list, detail panel, delete
- [Files](Frontend/Files-Page.md): file-drop page, upload, single-use download links
- [Shared components](Frontend/Shared-Components.md): responsive list, ButtonSelector, ConfirmDialog, formatting

### Services

- [Gateway](Services/Gateway.md): LAN access through the Nginx container
- [Hooks](Services/Hooks.md): toast hooks, relay hook, scheduled-task scripts
- [Widget](Services/Widget.md): floating live-sessions widget, startup shortcut, process ownership

### Ideas

- [Alert tiering ideas](Ideas/Alert-Tiering.md): parked plan for sorting alerts by urgency

<!-- jois-init:docs begin -->
## Pages

- [Alert tiering ideas](Ideas/Alert-Tiering.md)
- [Backend: API routes](Backend/API-Routes.md)
- [Backend: data layer](Backend/Data-Layer.md)
- [Backend: history store](Backend/History-Store.md)
- [Backend: live sessions and prompts](Backend/Live-Sessions-And-Prompts.md)
- [Backend: overview and query modules](Backend/Stats-And-Queries.md)
- [Backend: security](Backend/Security.md)
- [Coding standards](Contributing/Coding-Standards.md)
- [Frontend: API layer](Frontend/Api-Layer.md)
- [Frontend: files](Frontend/Files-Page.md)
- [Frontend: overview](Frontend/Overview-Page.md)
- [Frontend: projects](Frontend/Projects-Page.md)
- [Frontend: sessions](Frontend/Sessions-Page.md)
- [Frontend: shared components](Frontend/Shared-Components.md)
- [Frontend: shell and theme](Frontend/Shell-And-Theme.md)
- [Gateway](Services/Gateway.md)
- [Glossary](Glossary.md)
- [Guide: All sessions](User-Guide/All-Sessions.md)
- [Guide: Files](User-Guide/Files.md)
- [Guide: Getting started](User-Guide/Getting-Started.md)
- [Guide: Live sessions](User-Guide/Live-Sessions.md)
- [Guide: Notifications](User-Guide/Notifications.md)
- [Guide: Overview](User-Guide/Overview.md)
- [Guide: Projects](User-Guide/Projects.md)
- [Guide: Remote access](User-Guide/Remote-Access.md)
- [Guide: Settings](User-Guide/Settings.md)
- [Guide: Desktop widget](User-Guide/Widget.md)
- [Hooks](Services/Hooks.md)
- [Repository layout](Contributing/Repository-Layout.md)
- [Setup and run](Contributing/Setup-And-Run.md)
- [Testing](Contributing/Testing.md)
- [Widget](Services/Widget.md)
<!-- jois-init:docs end -->
