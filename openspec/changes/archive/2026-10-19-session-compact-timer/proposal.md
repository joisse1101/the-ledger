## Why

Long Claude Code sessions degrade, and today nothing says how long a session has been running since it started or was last compacted. The context size shows how heavy a session is, but not how stale it is. A time-based signal on the Live sessions page and in the desktop widget tells the user at a glance which sessions to compact.

## What Changes

- The backend finds the time of each live session's most recent compaction (its `compact_boundary` transcript line) and measures the session's age from the later of that time and the session's `started_at`. When the transcript is missing or unreadable, the age is measured from `started_at` alone.
- Each `/api/live` session gains a `compact` field: `{state, since}`. `state` is `ok` (under 45 min), `should` (45 to 55 min inclusive) or `needs` (over 55 min); `since` is the ISO timestamp the age is measured from. The thresholds are fixed constants on the server, not configurable. A session with no usable start time has `compact: null`.
- Live sessions page: a "Should compact" (amber) or "Needs compact" (red) pill on the row or card. Nothing is shown while `ok`. The pill is muted when the session's status is `idle`.
- Widget: a coloured dot to the left of every session row: green, amber or red for `ok`, `should` and `needs`. The dot is hollow (an outlined ring) when the session's status is `idle`.
- Widget: the tinted row backgrounds (pending, done, error) follow the widget's opacity setting like the window background, so the dot is the only fully opaque element on a row.
- The "only absolute token counts" requirement is clarified: a time-based compaction indicator is allowed, a token-based compaction threshold still is not.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `live-context-gauge`: the Live sessions list gains the compact-state pill and the server computes the state; the "only absolute token counts" requirement is clarified to permit a time-based indicator.
- `desktop-widget`: each row gains the compact-state dot, and the tinted row backgrounds follow the opacity setting.

## Impact

- `api/app/domain/context/` (compaction timestamp in `parsing.py`/`models.py`, newest-boundary lookup in `tail.py`), `api/app/domain/live_snapshot.py` (the `compact` field), with tests under `api/tests/domain/`.
- `web/src/api/types.ts` (`LiveSession.compact`), `web/src/components/sessions/LiveList.tsx` (pill, next to `PendingBadge`), styles under `web/src/styles/`, with a Vitest case in `LiveList.test.tsx`.
- `widget/src/shared/types.ts`, `widget/src/renderer/view.ts` and `style.css`, with widget tests.
- Wiki pages: Backend-API-Routes, Backend-Overview-And-Queries or Backend-Live-Sessions-And-Prompts (live item shape), Frontend-Sessions, Widget.
- Additive API change only: the new field never removes or repurposes an existing one.
