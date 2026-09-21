## 1. Turn parsing and formatting (pure functions in a new `claude_context.py`)

- [x] 1.1 Create `claude_context.py` and `tests/test_claude_context.py`; implement extraction of real main-thread turns from jsonl lines (assistant, not sidechain, model not `<synthetic>`, non-zero total, de-duplicated by `message.id` with the last line winning) and context = input + cache read + cache written. Verify tests pass for: cached tokens included (2 + 393,000 + 1,500 = 394,502), multi-block de-duplication, `<synthetic>`/zero-usage skipped, sidechain skipped.
- [x] 1.2 Implement token humanising (`742`, `81k`, `1.2M`, exact below 1,000, nearest thousand up to but below 1M, one decimal at 1M+). Verify tests cover 742 / 80,618 / 1,234,567 and the rounding boundary just below 1,000,000 (which must not print `1000k`). This is the same rule as `toast-token-usage` design Decision 6, so keep them in step.
- [x] 1.3 Implement growth and sparkline formatting: direction marker plus humanised delta, up to 24 recent turns, scaled from zero to the window max, size only when there is a single turn. Verify tests cover 390k to 394k rendering nearly flat, a shrink showing the downward marker and decrease, and the single-turn case.

## 2. Live tail-read

- [x] 2.1 Implement the backwards tail reader: start at a 256 KB window, double until 24 real turns are found or the file start is reached, drop the first line when the read did not begin at byte 0, skip lines that fail to parse. Verify with `write_transcript` fixtures: a trailing partial line is skipped, an empty file yields nothing, and a transcript with a line larger than the first window forces the window to double and still finds turns.
- [x] 2.2 Implement transcript location: `claude_db.projects_dir() / sanitize_project_path(cwd) / <session_id>.jsonl`, with a single `*/<session_id>.jsonl` glob fallback whose result is memoized; a missing file yields none. Verify tests under the `isolated_db` fixture cover the sanitized-path hit, the glob fallback, and the missing case.
- [x] 2.3 Add a stat-keyed cache on `(path, size, mtime_ns)`. Verify a test that an unchanged file is not re-read on a second call (count reader calls) and is re-read after an append.
- [x] 2.4 Add the public live entry point returning size, growth, and history for a session, or none, and never raising: OS and decode errors resolve to none. Verify a test with an unreadable path returns none, and time a call on the largest local transcript (about 10 MB) to confirm it stays in the low milliseconds.

## 3. Live table column

- [x] 3.1 Add a Context value to each row built in `views/sessions_data.py`'s `_sessions_dataframe`, computed per refresh outside `load_sessions()`'s registry-mtime cache, with `--` when unavailable and a failure on one session isolated from the others. Verify by extending `tests/test_views.py`: a stubbed loader gives the formatted cell, a session with none gives `--`, and one session raising leaves the other rows populated.
- [x] 3.2 Add `Context` to `_LIVE_COLUMNS` and a matching entry to `_LIVE_WIDTHS` in `views/sessions_live.py`. Verify by running the app: the column appears, this session's row shows a size that changes as new responses are written within one refresh tick, a just-started session shows a size before any manual refresh of the app's data, and no percentage or limit appears anywhere.

## 4. Detail-view data (pure functions)

- [x] 4.1 Implement the full-transcript parse producing per-turn records (new, cache read, cache written, output, timestamp, tool names with short hints) and compaction events from `compact_boundary` lines. Verify tests cover ordering, tool hint extraction (file path or command), and compaction positions.
- [x] 4.2 Implement the cache-miss flag: a turn other than the first that wrote more cached tokens than it read. Verify tests: 168,000 written vs 41,000 read is flagged, 150,000 read vs 500 written is not, and a first turn that wrote more than it read is not.
- [x] 4.3 Implement growth attribution: the delta at each turn goes to the first tool called in the previous turn (or "prompt / text" when none), grouped by tool with totals and counts, restarting after the latest compaction, plus the five largest single-turn increases with tool and hint. Verify tests for the reconciliation invariant (first-turn context + attributed growth = latest context), grouping totals, top-five ordering, and restart after compaction. Then sanity-check on the real local transcript `c2cf6150-07ea-4320-885a-cfb7ada6539b.jsonl`: 57,679 + 372,294 must equal 429,973.
- [x] 4.4 Memoize the full parse by `(path, size, mtime_ns)`. Verify a test that a repeat call on an unchanged file does not re-parse and a grown file does.

## 5. Detail view (UI)

- [x] 5.1 Wire the row's click hook in `views/sessions_live.py` (currently `on_click=lambda: None`) to select a session in `st.session_state`. Spike an `st.dialog` first and confirm it survives the Live fragment's 2s reruns by opening it and waiting well past several ticks; if it closes, use an inline panel below the table instead. Verify the chosen container stays open across ticks, then record the outcome under Open Questions in `design.md`.
- [x] 5.2 Render the per-response history: new / cache read / cache written / output per response in order, cache-miss and compaction markers, in absolute tokens only, following the app's existing chart conventions and theme colors in `views/overview.py`. Verify by running the app against a live session and against the largest local session: the miss and compaction markers appear where the data has them, and nothing is shown as a percentage of a limit.
- [x] 5.3 Render "what filled the context": the by-tool table (tokens and uses) and the five largest increases with hints. Verify against the local transcript from task 4.3: the by-tool totals match the numbers there.

## 6. Documentation and final verification

- [x] 6.1 Update `CLAUDE.md`'s architecture notes for the new module and behavior: `claude_context.py`, the Live Context column reading transcripts outside SQLite, the detail view, and the chosen detail-view container from task 5.1. Verify by reading the diff: each of those is described and nothing in the existing bullets is now wrong.
- [x] 6.2 Run the full suite and the spec scenarios. Verify `pytest` passes, `openspec validate live-context-gauge --strict` reports valid, and each scenario in `specs/live-context-gauge/spec.md` has been checked in the running app or by a test.
