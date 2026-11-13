# Proposal

## Why

The compact indicator counts its hour from the session's start or last compaction. Claude's prompt cache lasts one hour from the most recent request, and every request refreshes it, including the ones that send a tool result back. A session that is worked on all day therefore shows "Needs compact" while its cache is fresh, and an idle one stays green for too long.

## What Changes

- Grade a live session by the time since its latest activity: the timestamp of the newest `user` line in the main conversation, which is the request that last reached Claude. Tool results count, as each is an API call.
- Keep the thresholds and colours: `ok` (green) under 45 minutes, `should` (amber) from 45 to 55 minutes inclusive, `needs` (red) over 55 minutes.
- Drop the separate last-compaction lookup. A compaction writes new lines, so it already restarts the clock.
- Fall back to the session's start when the conversation has no `user` line or cannot be read.
- Ignore sub-agent requests. They do not refresh the main agent's cache.
- The `compact` field's `since` now holds the moment of the latest activity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `live-context-gauge`: the requirement "Live sessions are graded by time since start or last compaction" becomes a grade by time since latest activity, with new scenarios.

## Impact

- Backend: `api/app/domain/compact_grade.py`, `api/app/domain/live_snapshot.py`, and the removal of `latest_compaction` and its cache from `api/app/domain/context/tail.py`. Their tests change in `api/tests/domain/`.
- API: `compact.since` in `/api/live` changes meaning; its shape does not.
- Frontend and widget: no code change. They read `compact.state` only.
- Docs: `wiki/Glossary.md`, `wiki/Backend/Live-Sessions-And-Prompts.md`, `wiki/Backend/API-Routes.md`.
