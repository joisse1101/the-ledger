## Context

See proposal.md for why. Current state:

- `LiveSnapshot` (`api/app/domain/live_snapshot.py`) builds each `/api/live` item once per second for all clients. Its injected `clock` is `time.monotonic` and only drives the TTL, so it can't be used to measure elapsed wall-clock time.
- The registry's `started_at` is a naive local datetime (built with `datetime.fromtimestamp`), while transcript line timestamps are ISO strings that may be timezone-aware UTC.
- `compact_boundary` lines are already recognised in `parsing.scan` (`api/app/domain/context/parsing.py`), but the `Compaction` model keeps no timestamp. The live path (`tail.py`) reads only the last 256 KB of a transcript, doubling the window until it finds enough data, and caches per transcript by `(size, mtime)`.
- The web `LiveSession` type mirrors the server JSON by hand (`web/src/api/types.ts`); the widget keeps its own copy of the fields it uses (`widget/src/shared/types.ts`). The widget imports nothing from `web/`.
- The widget's page background follows `--bg-alpha`, but the `.pending`, `.done` and `.error` row tints use opaque colours.

## Goals / Non-Goals

**Goals:**
- One grade per live session, computed on the server, so the dashboard and the widget can't disagree.
- No new transcript scan cost: reuse the stat-keyed cache and the tail-window approach.

**Non-Goals:**
- Configurable thresholds (fixed constants, per the request).
- Counting only active time, or grading by tokens.
- Notifications or toasts when a session crosses a threshold.
- Changing the grade of sessions that have ended (only live sessions are graded).

## Decisions

**1. The server sends `compact: {state, since} | null` on each live item.**
`since` is the anchor (the later of `started_at` and the newest compaction) as a timezone-aware ISO string; `state` is `ok | should | needs`. Alternatives: send only `since` and let each client apply the bands (duplicates the thresholds in TypeScript twice and lets them drift), or send elapsed seconds (stale between polls, and the client clock is not trusted). Sending `since` as well as `state` lets a client show a tooltip such as "Compacted 52 min ago" later without another API change. The change is additive; no existing field changes.

**2. Newest compaction time comes from a new tail lookup, not from `scan`.**
Add `tail.latest_compaction(session_id, cwd)`, shaped like the existing `latest_activity`: it reads backwards from EOF in a doubling window until it finds a `compact_boundary` line or reaches the start of the file, caches per path by `(size, mtime)`, and never raises (returns `None` on `OSError`/`ValueError`). Reusing `scan` would parse every turn of a large transcript for one timestamp. The `Compaction` model gains an optional `timestamp` so the detail view can use it later, but nothing in this change reads it from there. A search that has to reach the start of a large never-compacted transcript is paid once per `(size, mtime)` change, which is the same cost class as `latest_activity`.

**3. Grading is a pure function with an injected wall clock.**
A small pure function `grade_compact(started_at, last_compaction, now)` returns the state and anchor; thresholds are module constants (`SHOULD_COMPACT_AFTER = 45 min`, `NEEDS_COMPACT_AFTER = 55 min`). `LiveSnapshot` takes a `now: Callable[[], datetime]` (default: current UTC time) next to its existing `clock`, so tests control time without patching. Bands: under 45 min `ok`, 45 to 55 min inclusive `should`, over 55 min `needs`.

**4. Timezones are normalised before comparing.**
Naive datetimes (the registry's `started_at`) are treated as local time and converted to UTC; aware ones are converted to UTC. The `since` string is always aware UTC. The anchor is always the later of `started_at` and the newest compaction, so a compaction timestamp that is earlier than `started_at` (clock skew) is ignored.

**5. A failed compaction lookup degrades to `started_at`.**
Matching how `_context` and `_branches` already swallow a failing read, the compaction lookup returns `None` on any failure and the grade then uses `started_at` alone. No `started_at` means `compact: null`.

**6. Web: a pill next to `PendingBadge`.**
`LiveList` adds a `CompactBadge` rendered in the existing `rowBadge` slot and as a table cell, reusing the `pending-badge` look with amber and red variants from `tokens.css` colours. Idle sessions get a muted variant (reduced emphasis, same text). `ok` and `null` render nothing. The pill sits on the auto-refresh the list already has.

**7. Widget: a dot element, hollow when idle, and tints that follow the opacity.**
`renderRow` adds a leading `span.compact-dot` with a state class; an absent grade renders an empty fixed-width placeholder so names stay aligned. Idle rows add a modifier that draws an outline instead of a fill. The new class is not named `.dot`, which belongs to the Remote toggle. Row tints (`.pending`, `.done`, `.error`) are rewritten with `color-mix(in srgb, var(--*-bg) calc(var(--bg-alpha) * 100%), transparent)`, like the body background, so only text and the dot stay opaque. The dot's colours come from the widget's existing `--status-ok` / `--status-busy` / `--status-bad` variables.

The idle ring resolves the earlier concern that a green dot could be confused with the green "done" row tint: idle rows are exactly the green-tinted ones, and they show a ring, not a fill.

## Risks / Trade-offs

- [A compaction deep in a very large transcript makes the backward search read a lot] → The result is cached by `(size, mtime)`, the window doubles as `latest_activity` does, and a failure falls back to `started_at`.
- [`since` uses the registry's start time, which may reflect a resumed session rather than the original conversation] → Accepted: the grade follows what the registry calls the session's start, and the compaction time wins when later.
- [The 1-second snapshot TTL means a grade can lag a threshold by about a second] → Negligible against 45-minute bands.
- [Tint rewrite changes the widget's look at partial opacity] → That is the intended effect; at full opacity the colours are identical, which a test checks.
- [Widget and web types are copied by hand] → The task list changes both types in the same commit, per the shared-contract rule.

## Migration Plan

Additive: no stored data or existing field changes. Roll back by reverting the change; older clients ignore the extra `compact` field.
