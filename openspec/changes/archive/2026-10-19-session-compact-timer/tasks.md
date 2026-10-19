## 1. Backend: compaction time and grade

- [x] 1.1 Add an optional `timestamp` to the `Compaction` model and fill it in `parsing.scan`; verify with a `test_context.py` case that a `compact_boundary` line's timestamp is kept and a missing one gives `None`
- [x] 1.2 Add `tail.latest_compaction(session_id, cwd)` (backward doubling window, stat-keyed cache, never raises); verify with `test_context.py` cases for no compaction, one, two (newest wins), a boundary beyond the first window, and an unreadable file
- [x] 1.3 Add the pure `grade_compact(started_at, last_compaction, now)` with the 45/55-minute constants and UTC normalisation of naive and aware datetimes; verify with unit tests for 20, 45, 55 and 55m01s, a compaction newer than the start, an older compaction, a naive `started_at`, and no start time
- [x] 1.4 Give `LiveSnapshot` an injectable `now` and a `latest_compaction` loader, and add `compact: {state, since} | null` to each live item, falling back to `started_at` when the lookup fails; verify in `test_live_snapshot.py` that a failing lookup leaves the other fields and rows intact and that the grade moves after the injected time advances past the TTL
- [x] 1.5 Run `cd api; pytest` and confirm it passes, including `test_layers.py`

## 2. Dashboard: compact pill

- [x] 2.1 Add `compact` to `LiveSession` in `web/src/api/types.ts`
- [x] 2.2 Add a `CompactBadge` to `LiveList.tsx` (amber "Should compact", red "Needs compact", nothing for `ok`/null, muted when `status` is `idle`) in the card badge slot and as a table cell, with token-based colours in the stylesheet; verify with `LiveList.test.tsx` cases for each state, the idle variant, and the pill disappearing when the next poll returns `ok`
- [x] 2.3 Run `cd web; npm test; npm run build` and confirm both pass; check the table and card layouts by resizing a real browser

## 3. Widget: dot and opacity-following tints

- [x] 3.1 Add `compact` to `LiveSession` in `widget/src/shared/types.ts`
- [x] 3.2 Render a leading `compact-dot` in `renderRow` (state class, hollow when idle, empty aligned placeholder when no grade); verify with `widget` Vitest cases for the three states, idle ring, no-grade alignment and that clicking the row still opens the repo
- [x] 3.3 Rewrite the `.pending`, `.done` and `.error` tints in `style.css` to follow `--bg-alpha`, and style the dot at full opacity with the existing status colour variables; verify with a test that the tint classes are still applied and by viewing the widget at low and full opacity
- [x] 3.4 Run `cd widget; npm test; npm run build` and confirm both pass

## 4. Docs

- [x] 4.1 Update the wiki pages for the changed behavior (Backend-API-Routes live item shape, Frontend-Sessions, Widget) and verify `cd api; python check_docs.py` passes
