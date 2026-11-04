# Glossary

Plain-English meanings of the terms used across the wiki. Link to an entry here instead of redefining it.

## Sessions

### Session

One conversation with Claude Code, recorded as a transcript on disk. The dashboard lists sessions under Sessions and groups them into projects.

### Live session

A session whose Claude Code process is running now, found in Claude Code's registry at `~/.claude/sessions/<pid>.json`. The Live page shows these. See [Live sessions and prompts](Backend/Live-Sessions-And-Prompts.md).

### Pending decision

A prompt a live session is blocked on, such as a tool-permission dialog or a question. It can be answered from the dashboard or from the terminal; whichever answers first wins. The [relay hook](#relay-hook) is what delivers these prompts to the backend.

### Auto-approve

A per-session switch that answers `allow` to pending decisions automatically. It never approves questions or plan exits, and it skips commands that look dangerous. It is in memory only, off after a backend restart, and only the machine running the app can turn it on.

### Compact

Claude Code's compaction, which summarizes a long conversation to free context space. The dashboard grades each live session by time since the last compaction: `ok`, `should` (after 45 minutes) or `needs` (after 55 minutes).

## Access

### Remote mode

A switch that lets other devices on your network see and answer live sessions. Turning it on starts Docker, the frontend and the [gateway](#gateway), then shows a sign-in QR code. It is in memory only and turns itself off after 8 hours. See [Gateway](Services/Gateway.md).

### Gateway

The Nginx container that is the only way another device reaches the app. It serves HTTPS with a self-signed certificate. See [Gateway](Services/Gateway.md).

### Access token

A secret that a remote device sends to prove it may use the API. It is made when Remote mode turns on, kept only in memory, and encoded in the sign-in QR code. See [Security](Backend/Security.md).

## Data and hooks

### Relay hook

An optional Claude Code `PermissionRequest` hook that sends permission prompts to the backend. Without it, the dashboard cannot show or answer pending decisions. See [Hooks](Services/Hooks.md).

### History store

A durable SQLite file, `api/.history/history.db`, that keeps transcripts after Claude Code prunes them from disk. Unlike the snapshot database, nothing wipes it. See [History store](Backend/History-Store.md).
