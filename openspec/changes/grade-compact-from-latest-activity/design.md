# Design

## Context

`LiveSnapshot._compact` grades from `session.started_at` and `tail.latest_compaction`, through the pure `compact_grade.grade_compact`. `tail.latest_activity` already returns the newest `user` line's timestamp from the main transcript, cached per file by its size and modification time, and `LiveSnapshot` already holds it as `_latest_activity` for the pending-prompt sweep. Sub-agent requests are written to separate transcript files, so the main transcript never contains them. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- Reuse `latest_activity` as the single definition of "latest activity".
- Keep `grade_compact` pure, with the same thresholds and boundary rules.

**Non-Goals:**
- No change to the pill, the widget dot or their colours.
- No change to what `latest_activity` counts, since the pending-prompt sweep depends on it.

## Decisions

- **Anchor is the later of latest activity and session start.** `grade_compact(started_at, latest_activity, now)` keeps its shape and takes the later of the two, so the start is the floor when no `user` line exists. The later-of rule keeps the old fallback without a new branch. Alternative: use activity alone and fall back only when it is missing. Rejected: same result, more code.
- **Count every `user` line.** A tool result is a request to Claude and refreshes its prompt cache, so the existing reader is right as it is. Alternative: write a reader for typed prompts only. Rejected: it would be wrong about the cache.
- **Remove `latest_compaction`.** Compaction writes new lines, which move the latest activity. The function, its cache and its tests go.
- **Failure handling is unchanged.** A failing lookup is treated as no activity, so the grade runs from the start. `tail.latest_activity` never raises.
- **`since` keeps its name.** It now carries the anchor, which is the latest activity, so clients need no change.

## Risks / Trade-offs

- [A few `user` lines, such as local slash-command echoes, may not trigger an API call, so the clock restarts slightly early] → Accepted; the effect is small.
- [`compact.since` changes meaning for any client that displays it] → The web and widget clients read `state` only; checked during apply.
