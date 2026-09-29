# The Ledger

A dashboard for viewing your local Claude Code sessions and projects: Overview, Sessions (Live and
All), and Projects. An API-only FastAPI backend (`api/`) plus a React + Vite frontend (`web/`),
readable from another device on the same network through a gateway, behind a shared access token.

> **Edit these pages in the repo (`wiki/`), not on the GitHub wiki.** The wiki is a one-way mirror
> published on every push to `main`; edits made in the browser are overwritten.

Requirements live in `openspec/specs/`, not here.

## Pages

**Getting started**
- [Setup and run](Setup-And-Run.md): install, start, ports, history backup task
- [Testing](Testing.md): running the Python and frontend suites
- [Repository layout](Repository-Layout.md): folders, gitignored state, OpenSpec
- [Coding standards](Coding-Standards.md): what "human-understandable" means here

**Backend**
- [Data layer](Backend-Data-Layer.md): SQLite snapshot, projects, transcripts, live sessions, context
- [History store](Backend-History-Store.md): durable history and the backup script
- [API routes](Backend-API-Routes.md): the route table and server startup
- [Security](Backend-Security.md): access token, local vs. remote, CSRF header
- [Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md): live snapshot, pending decisions, Remote mode
- [Overview and queries](Backend-Overview-And-Queries.md): aggregation and filter/sort modules

**Frontend**
- [API layer](Frontend-Api-Layer.md): stack, sign-in token, fetch client, query hooks
- [Shell and theme](Frontend-Shell-And-Theme.md): app shell, viewport classes, theme tokens
- [Sessions](Frontend-Sessions.md): Live and All pages, dialogs, prompts
- [Overview](Frontend-Overview.md): charts and summary stats
- [Projects](Frontend-Projects.md): project list, detail panel, delete
- [Shared components](Frontend-Shared-Components.md): responsive list, ButtonSelector, ConfirmDialog, formatting

**Services**
- [Gateway](Gateway.md): LAN access through the Nginx container
- [Hooks](Hooks.md): toast hooks, relay hook, scheduled-task scripts
