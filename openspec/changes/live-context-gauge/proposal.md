## Why

The Live sessions table says nothing about how much a session is sending to Claude, so there's no signal for when to compact. The transcript already records exact per-turn token usage, so a live context size can be read without estimating. Cost, the only usage measure the app shows today, is the wrong lens for a running session: it says what you've spent, not how full the context is.

## What Changes

- Add a **Context** column to the Live table: the session's current context size in absolute tokens, the growth from the last turn, and a small sparkline of context over recent turns. Context is `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` on the latest real main-thread assistant turn.
- Read context by tail-reading each live session's transcript (`~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl`), on the Live table's existing 2s poll and outside the SQLite snapshot. Zero-usage and `<synthetic>` turns are skipped so an API-error line can't read as a context collapse.
- Add a per-session detail view, opened from a Live row, showing exact token history for that session:
  - cache read / cache written / fresh input per turn
  - cache-miss and compaction markers
  - what filled the context: growth attributed to the tool that produced it (from per-turn context deltas, not character counts), plus the largest single-turn increases
- Everything is absolute tokens. No percentage, no model context-window table, no compaction threshold, and no cache hit rate on the Live row.

### Out of scope

- Authoritative session cost from the `cost-state` transcript line, covered by the separate `authoritative-session-cost` change.
- Moving the Overview page, or the All sessions table, from cost/messages to tokens.
- Subagent transcripts (`<session-id>/subagents/`). Subagents have their own contexts, so they don't affect the main thread's context size.

## Capabilities

### New Capabilities
- `live-context-gauge`: showing a live session's current context size, its recent growth, and a per-session token/cache history with growth attributed to tools.

### Modified Capabilities

None. There are no existing specs under `openspec/specs/`.

## Impact

- `claude_context.py` (new): tail-reads a live session's transcript for its context size and recent history, and fully parses one on demand for the detail view.
- `views/sessions_live.py`, `views/sessions_data.py`: a new Context column and a detail view opened from a row's existing click hook.
- `claude_db.py`: reuses `sanitize_project_path()` / `projects_dir()` to locate the transcript; no schema change, since live context bypasses the SQLite snapshot.
- Tests: pure functions for tail-read parsing, synthetic/zero-usage filtering, context deltas, and tool attribution, following the existing one-file-per-module layout under `tests/`.
- No new dependencies.
