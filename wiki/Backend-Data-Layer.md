# Backend: data layer

This page explains how the backend reads Claude Code's files from disk and keeps them in a SQLite snapshot. Read it to learn which module owns which data and how a refresh, a delete and a live-context read work.

> Requirements live in `openspec/specs/live-context-gauge/spec.md`, `openspec/specs/transcript-history/spec.md`. This page describes how the code meets them, not what it must do.

## Overview

These modules live in `api/` alongside the server, their only consumer. They are plain Python with no FastAPI or Starlette dependency of their own. Keeping them framework-free keeps the pure data layer testable and readable independent of the web framework wrapping it.

## `api/app/repositories/db/`

### What it is

It is the single SQLite-backed store that `claude_projects.py` and `claude_transcripts.py` both read from. They used to each scan and mtime-cache their own files on disk.

All of the disk-reading lives here: `~/.claude.json` and `~/.claude/projects/*/*.jsonl` parsing, the `_MODEL_PRICING` table, `sanitize_project_path()` and so on.

### Its files

- `paths.py` holds where files live.
- `connection.py` holds connections and schemas.
- `scanner.py` does the disk parsing.
- `snapshot.py` holds `refresh` and `startup`.
- `queries.py` holds reads and deletes.
- `history.py` holds the durable `history.db`.

### Refreshing

`refresh()` rescans both sources. It resolves each transcript's `project` from the just-scanned project list. It matches the transcript's on-disk parent folder against `sanitize_project_path()`. It replaces the `projects` and `transcripts` tables' contents in one pass. It stamps a `meta.refreshed_at` timestamp. `refreshed_at()` reads that timestamp back.

This is the only place disk gets rescanned. It runs in three ways:

- explicitly, via `POST /api/refresh`
- once automatically, via `startup()` on process start
- on a periodic 10-minute `asyncio` loop task (see `api/app/refresh.py`)

### Startup and the database file

`startup()` treats the database as a pure derived cache. It deletes any leftover db file from a previous run. It calls `refresh()` to rebuild it from disk. It registers an `atexit` handler to delete it again on exit, best-effort. `startup()` and its `atexit` hook also clean up the `-wal` and `-shm` files.

`db_path()` returns `api/.ledger/ledger.db` (gitignored).

### Connections

`_connect()` sets `PRAGMA journal_mode=WAL` and a busy timeout. That suits the FastAPI server's concurrent-request model. Multiple browsers or phones read while a background `refresh()` writes.

### Reading

`load_projects()` and `load_transcripts()` just `SELECT * ... ORDER BY` these tables. They build dataclasses from the rows. They are cheap enough to call fresh on every request or rerun, with no caching of their own.

### Deleting

`delete_project()`, `delete_project_transcripts()` and `delete_transcript()` each mutate the real on-disk source first. They then delete just the matching row or rows from SQLite by key. They do not call `refresh()` again. A full rescan is not needed, since the key just removed from disk is exactly the key to remove from the db.

## `claude_projects.py`

It holds the `ClaudeProject` dataclass and query and delete functions for Claude Code's project data.

The data originally comes from `~/.claude.json`'s top-level `projects` map. That map has one entry per directory Claude Code has been run or trusted in. It reflects only that project's last session. It holds trust status, last session ID, CLI version, cost, start time, lines added and removed, and any project-scoped MCP servers.

`delete_project(project_path)` edits `~/.claude.json` directly, the real source of truth. It then removes the matching row from SQLite via `queries.delete_project_row()`.

## `claude_transcripts.py`

### What it holds

It holds the `ClaudeTranscript` dataclass and query and delete functions for session transcript data. The data is originally parsed line by line from `~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl`. That covers every session that has ever run, including exited ones. The parsing itself lives in `snapshot.refresh()`.

### What the parsing derives

`started_at` and `updated_at` are the min and max line timestamp. `message_count` counts non-meta `user` and `assistant` lines.

`context` is the same latest-real-main-thread-turn figure `api/app/domain/context/` shows live, via `scanner._context_tokens`.

`cost` prices each turn's `message.usage` via `_MODEL_PRICING`. It is counted once per unique `message.id`. It is an estimate: unrecognized models are silently skipped.

`model` is the model with the most main-thread responses. It counts once per `message.id`. It ignores `<synthetic>`. Ties go to the first seen.

`used_openspec` is set by a `/opsx:*` slash command, or an `openspec-*` or `opsx:*` Skill call, anywhere in the session.

`project` matches the on-disk parent folder against each project's `sanitize_project_path()`. It falls back to a guess derived from the cwd or folder.

`worktree` is described next.

### Worktree sessions

A session whose first `cwd` is under `<repo>/<folder>/<name>` is a worktree session. `<folder>` is `.claude/worktrees` or any folder listed in the Settings page. `api/app/core/worktrees.py`'s `parse_worktree` recognises it, trying the longest folder first. The session stores that `<name>`. It belongs to its repo's project, instead of showing up as a project named after the worktree. <!-- docs-check: ignore -->

`ClaudeTranscript.project_folder` is the `~/.claude/projects/` folder a transcript counts under. It is the transcript's own folder. For a worktree session it is the repo's, with the sanitized `/<folder>/<name>` suffix stripped off, via `paths.repo_folder_of_worktree`.

### Deleting

`delete_project_transcripts(cwd)` removes every folder holding a member transcript. It skips a folder that also holds non-members. `delete_transcript(session_id)` removes one transcript.

Both look up the affected path or paths via `queries`. Both remove the real files, tolerating one already gone. See [History store](Backend-History-Store.md). Both then delete just those rows from both `ledger.db` and `history.db`.

## `settings_store.py`

### Where settings live

It keeps the user's worktree folders in `api/.ledger/settings.json` (gitignored). `LEDGER_SETTINGS_PATH` overrides the path. The test suite points it at a temp file. Only user folders are stored; `.claude/worktrees` is built in. <!-- docs-check: ignore -->

### Reading

`load_worktree_folders()` re-reads the file only when its mtime or size changes. A missing or unreadable file reads as no folders. It skips entries that fail `normalize_folder`, with a warning.

The file also holds `widget_max_projects`, how many projects the widget's tooltip lists. `load_max_projects()` reads it. A missing or out-of-range value reads as 5.

The file also holds `widget_afk_minutes`, how long the widget's AFK switch stays on. `load_afk_minutes()` reads it. A missing or out-of-range value reads as 30.

### Saving

The saves are `save_worktree_folders()`, `save_max_projects()` and `save_afk_minutes()`. Each is a read-modify-write under a lock. It sets one key and keeps the others, unknown keys too. It writes a temp file and `os.replace`s it.

### Who reads it

The scanner, `paths.project_folder` and `history.correct_worktree_rows` all read it. So `backup_history.py` follows the same list with no wiring of its own.

## `claude_sessions.py`

### What it does

It parses Claude Code's live session registry at `~/.claude/sessions/<pid>.json`, one file per process. It reads directly from disk on every call. Unlike projects and transcripts, it is not routed through `api/app/repositories/db/`. The Live views poll it every ~2s, and a snapshot refreshed only on demand would defeat that.

### What it returns

`load_sessions()` returns `ClaudeSession` dataclasses sorted by `updated_at` descending. It has its own module-level cache keyed by each file's mtime. Dead PIDs' files may linger, so entries are not guaranteed to reflect live processes.

### How it fills in fields

Each session's `project` comes from looking up its `session_id` in `claude_transcripts.load_transcripts()`. It reuses that transcript's `project`. It falls back to a `cwd`-derived guess for a brand-new session with nothing written to disk yet.

The same lookup replaces `started_at` with the transcript's earliest timestamp. The registry's `startedAt` is per process, so closing and reopening a session resets it. It stays only as the fallback until the transcript has a timestamped line.

## `api/app/domain/context/`

### What it is

It reads a live session's token usage straight from its transcript. It sits outside `api/app/repositories/db/` (SQLite), for the same reason `claude_sessions.py` does. The transcript is located from the registry's `cwd` and session ID. It falls back to one memoized `*/<session-id>.jsonl` glob.

### Its files

- `models.py` holds dataclasses.
- `parsing.py` turns transcript lines into turns.
- `tail.py` gets live context and latest activity from the file's tail.
- `detail.py` builds the full per-session detail.
- `attribution.py`, `breakdown.py` and `formatting.py` hold the rest.

### What "context" means

**Context** is the latest real main-thread assistant turn's `input + cache_read + cache_creation` tokens. "Real" means all of these:

- not `isSidechain`
- model not `<synthetic>`
- non-zero usage
- de-duplicated by `message.id`

### Live context

`live_context()` tail-reads backwards from EOF in a doubling window. It is memoized by `(path, size, mtime_ns)`. It returns a `LiveContext(size, growth, history)` or `None`, and never raises.

`format_context()` renders `394k ▲ +2.1k ▁▂▃…`. `humanise_tokens` formats the sizes. Growth uses a one-decimal `k`. The sparkline is made of block glyphs, scaled 0 to the window max.

The API's `live_snapshot.py` calls this function directly. So the Live list's `label` text comes straight from it.

### Detail and attribution

For the detail dialog or view, `load_detail()` fully parses the transcript on demand. It builds per-turn records plus `compact_boundary` compactions.

Growth attribution credits each turn's context delta to the first tool called in the previous turn, or "prompt / text". It counts since the latest compaction. `first-turn context + attributed growth == current context` holds exactly. It reads the main thread only; subagent transcripts are ignored.

### Breakdown

The same scan also collects the startup-content `attachment` entries. They are `instructions`, `skill_listing`, `agent_listing_delta` and `mcp_instructions_delta`. They are kept as events keyed by how many responses preceded them.

`build_breakdown()` turns them into `SessionDetail.breakdown`. It holds three things:

- Startup snapshots: memory files, skills, custom agents and MCP instructions, each itemised. They are estimated as `chars/4`. They are scaled down so they never exceed the segment's first response. <!-- docs-check: ignore -->
- Per response, the exact cumulative growth by tool since the segment start. A segment restarts at each compaction. The crediting rule is the same as the attribution.
- A remainder: system prompt, built-in tools and compaction summary.

So every response's rows sum to its exact context. Initial listings replace a category; later ones add. No removal has ever been seen in a real transcript.

A bad attachment drops the breakdown, as `None`, logged with the session id. It never drops the detail.
