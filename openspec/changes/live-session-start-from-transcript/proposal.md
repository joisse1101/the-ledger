## Why

A live session's start time comes from the registry file Claude Code writes per process (`~/.claude/sessions/<pid>.json`). Closing and reopening a session writes a new entry with a fresh `startedAt`, so the Live panel's "Started" time resets and the compact timer restarts from zero, even though the conversation (and its context) is the same one and may be 45 minutes or more old. Every other screen already uses the transcript's earliest timestamp, so Live also disagrees with the All sessions page for the same session.

## What Changes

- A live session's start time is the earliest timestamp in its transcript. The registry's `startedAt` is used only when the session has no transcript record yet.
- The same start time feeds the compact grade, so a reopened session keeps its true age and is flagged "Should compact" / "Needs compact" on schedule.
- No new field, schema column or API shape: `started_at` on each live item and the grade's `since` keep their names and formats.
- The earliest transcript line is not always the first prompt (a resumed session can have earlier non-prompt lines). This is accepted: it matches the All sessions page.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `live-context-gauge`: the requirement that grades live sessions by time since start or last compaction now defines "start" as the conversation's start (earliest transcript timestamp, registry start only as a fallback), with scenarios for a reopened session and for a session with no transcript yet.

## Impact

- Code: `api/app/repositories/claude_sessions.py` (`load_sessions` overlays the transcript's `started_at` next to the fields it already copies). `LiveSnapshot` and `grade_compact` are unchanged.
- Tests: `api/tests/repositories/test_claude_sessions.py`, `api/tests/domain/test_live_snapshot.py`.
- Docs: `wiki/Backend-Data-Layer.md` and `wiki/Backend-Live-Sessions-And-Prompts.md`.
- Clients: the web panel and widget read the same `started_at` / `compact` fields and need no change. `started_at` becomes timezone-aware (the transcript's UTC) instead of naive local time, which `Date` parsing in the web UI handles correctly.
