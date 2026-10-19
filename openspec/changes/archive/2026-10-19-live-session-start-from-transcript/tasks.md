## 1. Backend

- [x] 1.1 In `load_sessions()` (`api/app/repositories/claude_sessions.py`), copy the matching transcript's `started_at` onto the session when it is set, leaving the registry value otherwise; verify with `cd api; pytest tests/repositories/test_claude_sessions.py`
- [x] 1.2 Add tests there: a transcript's `started_at` replaces the registry's, and a session with no transcript match (or a transcript with no `started_at`) keeps the registry's; verify they fail without 1.1 and pass with it
- [x] 1.3 Add a `LiveSnapshot` test in `api/tests/domain/test_live_snapshot.py`: a session whose transcript began 50 minutes ago but whose registry start is 2 minutes ago is graded `should` and its item's `started_at` is the transcript's; verify with `cd api; pytest tests/domain/test_live_snapshot.py`

## 2. Docs

- [x] 2.1 Update `wiki/Backend-Data-Layer.md` (the `claude_sessions.py` entry) and `wiki/Backend-Live-Sessions-And-Prompts.md` to say a live session's start is the transcript's earliest timestamp, with the registry's `startedAt` as the fallback; verify with `cd api; python check_docs.py`

## 3. Verification

- [x] 3.1 Run the full backend suite with `cd api; pytest` and confirm it passes
- [x] 3.2 Run `openspec validate live-session-start-from-transcript` and confirm it reports the change valid
