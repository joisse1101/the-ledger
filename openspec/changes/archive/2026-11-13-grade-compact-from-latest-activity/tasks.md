## 1. Grading logic

- [x] 1.1 In `api/app/domain/compact_grade.py`, change `grade_compact` to take the latest activity instead of the last compaction, anchor on the later of it and `started_at`, and update the module docstring and the `since` comment. Satisfies "Live sessions are graded by time since start or last compaction".
- [x] 1.2 In `api/app/domain/live_snapshot.py`, make `_compact` read `self._latest_activity` (treating a failure as no activity) and remove the `latest_compaction` parameter and attribute.
- [x] 1.3 In `api/app/domain/context/tail.py`, remove `_read_tail_latest_compaction`, `_compaction_cache` and `latest_compaction`.

## 2. Tests

- [x] 2.1 Update `api/tests/domain/test_compact_grade.py` for the new input: the band and boundary cases, a new prompt restarting the clock, the fallback to start, and no grade without either time.
- [x] 2.2 Update the compact cases in `api/tests/domain/test_live_snapshot.py` to pass `latest_activity` instead of `latest_compaction`, including a failing lookup.
- [x] 2.3 Remove the four `latest_compaction` tests from `api/tests/domain/test_context.py`.

## 3. Docs

- [x] 3.1 Update `wiki/Glossary.md` (Compact entry), `wiki/Backend/Live-Sessions-And-Prompts.md` (The `compact` grade) and `wiki/Backend/API-Routes.md` (`compact` field) to say the grade runs from the latest activity.
- [x] 3.2 Run `python scripts/check_docs.py`.

## 4. Verify

- [x] 4.1 Run `cd api; pytest` and `cd web; npm test`, and confirm `web/` and `widget/` do not read `compact.since`.
