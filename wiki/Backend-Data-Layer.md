# Backend: data layer

> Requirements live in `openspec/specs/live-context-gauge/spec.md`, `openspec/specs/transcript-history/spec.md`. This page describes how the code meets them, not what it must do.

These modules live in `api/` alongside the server (their only consumer), but are plain Python with
no FastAPI/Starlette dependency of their own — keeping them framework-free keeps the pure data layer
testable and readable independent of the web framework wrapping it.

- `claude_db.py` is the single SQLite-backed store that `claude_projects.py` and
  `claude_transcripts.py` both read from, rather than each independently scanning and mtime-caching
  its own file(s) on disk as they used to. All of that disk-reading — `~/.claude.json` and
  `~/.claude/projects/*/*.jsonl` parsing, the `_MODEL_PRICING` table, `sanitize_project_path()`, etc.
  — lives here. `refresh()` rescans both sources, resolves each transcript's `project` from the
  just-scanned project list (matching the transcript's on-disk parent folder against
  `sanitize_project_path()`), replaces the `projects`/`transcripts` tables' contents in one pass, and
  stamps a `meta.refreshed_at` timestamp; `refreshed_at()` reads that timestamp back. This is the
  *only* place disk gets rescanned — triggered explicitly via `POST /api/refresh`, plus once
  automatically via `startup()` on process start, plus a periodic 10-minute `asyncio` loop task (see
  `api/server.py`). `startup()` treats the database as a pure derived cache: it deletes any leftover
  db file from a previous run, calls `refresh()` to rebuild it from disk, and registers an `atexit`
  handler to delete it again on exit (best-effort). `db_path()` returns `api/.ledger/ledger.db` (gitignored;
  that `.ledger/` is also where the LAN access token lives — see [Security](Backend-Security.md)).
  `_connect()` sets `PRAGMA journal_mode=WAL` and a busy timeout, for the FastAPI server's
  concurrent-request model (multiple browsers/phones reading while a background `refresh()` writes);
  `startup()`/its `atexit` hook also clean up the `-wal`/`-shm` files. `load_projects()` /
  `load_transcripts()` just `SELECT * ... ORDER BY` these tables and build dataclasses from the rows
  — cheap enough to call fresh on every request/rerun with no caching of their own. `delete_project()`
  / `delete_project_transcripts()` / `delete_transcript()` each mutate the real on-disk source first,
  then delete just the matching row(s) from SQLite by key, rather than calling `refresh()` again — a
  full rescan isn't needed since the key just removed from disk is exactly the key to remove from the
  db.

- `claude_projects.py` holds the `ClaudeProject` dataclass and query/delete functions for Claude
  Code's project data (originally `~/.claude.json`'s top-level `projects` map — one entry per
  directory Claude Code has been run/trusted in, reflecting only that project's *last* session:
  trust status, last session ID, CLI version, cost, start time, lines added/removed, any
  project-scoped MCP servers). `delete_project(project_path)` edits `~/.claude.json` directly (the
  real source of truth) then removes the matching row from SQLite via `claude_db.delete_project_row()`.
- `claude_transcripts.py` holds the `ClaudeTranscript` dataclass and query/delete functions for
  session transcript data (originally parsed line-by-line from
  `~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl` — every session that has ever run,
  including exited ones; the parsing itself lives in `claude_db.py`'s `refresh()`). That parsing
  derives `started_at`/`updated_at` (min/max line timestamp), `message_count` (non-meta `user`/
  `assistant` lines), `context` (the same latest-real-main-thread-turn figure `claude_context.py`
  shows live, via `claude_db._context_tokens`), `cost` (per-turn `message.usage` priced via
  `_MODEL_PRICING`, counted once per unique `message.id`; an *estimate* — unrecognized models are
  silently skipped), and `project` (matching the on-disk parent folder against each project's
  `sanitize_project_path()`, falling back to a cwd/folder-derived guess). `delete_project_transcripts(cwd)`
  and `delete_transcript(session_id)` look up the affected path(s) via `claude_db`, remove the real
  file(s) (tolerating one already gone — see [History store](Backend-History-Store.md)), then
  delete just those rows from both `ledger.db` and `history.db`.
- `claude_sessions.py` parses Claude Code's live session registry at `~/.claude/sessions/<pid>.json`
  (one file per process) directly from disk on every call — unlike projects/transcripts this isn't
  routed through `claude_db.py`, since the Live views poll it every ~2s and a snapshot refreshed only
  on demand would defeat that. `load_sessions()` returns `ClaudeSession` dataclasses sorted by
  `updated_at` descending, with its own module-level cache keyed by each file's mtime. Dead PIDs'
  files may linger, so entries aren't guaranteed to reflect live processes. Each session's `project`
  is resolved by looking up its `session_id` in `claude_transcripts.load_transcripts()` and reusing
  that transcript's `project`, falling back to a `cwd`-derived guess for a brand-new session with
  nothing written to disk yet.
- `claude_context.py` reads a live session's token usage straight from its transcript, outside
  `claude_db.py`/SQLite for the same reason `claude_sessions.py` is. The transcript is located from
  the registry's `cwd` and session ID, falling back to one memoized `*/<session-id>.jsonl` glob.
  **Context** is the latest real main-thread assistant turn's `input + cache_read + cache_creation`
  tokens ("real" = not `isSidechain`, model not `<synthetic>`, non-zero usage, de-duplicated by
  `message.id`). `live_context()` tail-reads backwards from EOF in a doubling window, memoized by
  `(path, size, mtime_ns)`; returns a `LiveContext(size, growth, history)` or `None`, never raises.
  `format_context()` renders `394k ▲ +2.1k ▁▂▃…` (`humanise_tokens` for sizes, one-decimal `k` for
  growth, a block-glyph sparkline scaled 0→window-max). The API's `live_snapshot.py` calls this
  function directly so the Live list's `label` text comes straight from it. For the detail dialog/
  view, `load_detail()` fully parses the transcript on demand into per-turn records plus
  `compact_boundary` compactions; growth attribution credits each turn's context delta to the first
  tool called in the previous turn (or "prompt / text"), since the latest compaction, with
  `first-turn context + attributed growth == current context` holding exactly. Main thread only —
  subagent transcripts are ignored.
