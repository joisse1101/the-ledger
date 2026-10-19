## Context

See proposal.md for why. Current state:

- `load_sessions()` (`api/app/repositories/claude_sessions.py`) parses each `~/.claude/sessions/<pid>.json` into a `ClaudeSession`, caches it by file mtime, then joins the transcripts snapshot by session id and copies `project`, `title`, `last_message` and `first_prompt` onto it. `started_at` is not among them, so it stays the registry's `startedAt` (a naive local datetime).
- The transcripts snapshot already holds `started_at`: the earliest line timestamp, an aware datetime (`scanner.py` parses ISO strings with their offset).
- `LiveSnapshot` builds the live item's `started_at` and the compact grade from `session.started_at` (`live_snapshot.py`); `grade_compact` already converts naive (local) and aware datetimes to UTC before comparing.
- The cached `ClaudeSession` objects are mutated in place by the join, and the join runs on every call.

## Goals / Non-Goals

**Goals:**
- One start time per live session that survives closing and reopening, used by both the "Started" display and the compact grade.

**Non-Goals:**
- Recording the exact first-prompt timestamp (a new scanner field and column). The earliest line is accepted, per the proposal.
- Changing the registry parse, the grade bands, the API shape or either client.

## Decisions

**1. Overlay in `load_sessions()`, beside the fields it already joins.**
When the matching transcript has a `started_at`, set `session.started_at` to it. Both consumers (`_item` and `_compact`) read `session.started_at`, so one assignment fixes the display and the grade and they cannot disagree. Alternatives: overlay in `LiveSnapshot` (needs a second transcript lookup there and splits one join across two layers), or add a separate `conversation_started_at` field (every consumer would then have to choose; the registry value has no other use).

**2. Fall back to the registry value only when the transcript has none.**
A brand-new session may not be in the snapshot yet, or has no timestamped line; then `started_at` stays as parsed, and the grade runs from it as before. The join leaves the field alone in that case, so it never blanks a known start.

**3. Accept the naive-to-aware change in the JSON.**
The live item's `started_at` becomes an aware ISO string (`...+00:00`) when it comes from the transcript, and stays naive local when it falls back. The web UI formats it with `Date`, which reads an aware string correctly; `grade_compact` normalises both. No client change is needed. Alternative: convert the transcript value to naive local to keep the format constant, which adds code to preserve an ambiguity the app is better off without.

## Risks / Trade-offs

- [The earliest line may be a non-prompt line, so the start can be slightly earlier than the first prompt] → Accepted in the proposal; it is the definition the All sessions page already uses.
- [The overlay mutates a cached object, so a value set once could outlive the transcript row (for example if the transcript is deleted while the session stays live)] → The join runs on every call and reassigns whenever a row exists; with no row the last overlaid value remains, which is still the conversation's true start. No reset is added.
- [A resumed session that writes a new transcript file under a new session id would still restart] → Not observed here and out of scope; the current join is by session id only.
