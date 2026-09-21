## Context

See proposal.md for motivation. Constraints that shape the approach:

- The Live table is an `@st.fragment(run_every="2s")` that rebuilds `_sessions_dataframe()` from `claude_sessions.load_sessions()`, which reads `~/.claude/sessions/<pid>.json` straight from disk and deliberately bypasses the SQLite snapshot (an on-demand snapshot would defeat the polling). Live context has the same requirement.
- `load_sessions()` caches each session by its registry file's mtime. Context changes when the *transcript* grows, which does not touch the registry file, so context can't live in that cache.
- Live rows are `st.columns` + `col.write(text)` (`views/sessions_table.py`), so any new cell is text. Each row already carries an invisible full-row button whose `on_click` is currently `lambda: None`.
- Each assistant line in a transcript carries `message.usage`. A multi-block turn repeats the same `message.id` and usage on every line, so lines must be de-duplicated by id.
- Transcript facts verified against local data: every cache write seen was the 1h tier; `compact_boundary` system lines carry `compactMetadata.preTokens/postTokens`; API-error turns appear as `<synthetic>` model lines with all-zero usage; subagent turns are in separate `<session-id>/subagents/*.jsonl` files, not in the main transcript.

## Goals / Non-Goals

**Goals:**
- A context reading that costs about 1 ms per live session and is safe on the 2s poll.
- A detail view whose numbers reconcile exactly with the API-reported usage, with no estimation.

**Non-Goals:**
- No percentage, model context-window table, or compaction threshold anywhere. Nothing in the transcript defines these, so the app would be guessing.
- No storage in SQLite and no schema change.
- No alerts or notifications (e.g. a toast at N tokens). Possible later via the existing `hooks/` work.
- No attribution by content type from character counts (see Decision 6).

## Decisions

**1. A new `claude_context.py`, split into pure parsing and thin file I/O.** Pure functions take an iterable of jsonl lines and return records. A small I/O layer does the seeking and caching. This mirrors how the repo separates parsing from Streamlit rendering, and keeps tests to plain functions.
*Alternatives:* fold it into `claude_sessions.py` (already mixes registry parsing with transcript joins), or into `claude_db.refresh()` (rejected: refresh-on-demand can't drive a 2s gauge).

**2. Locate the transcript from the registry, not the snapshot.** Path is `claude_db.projects_dir() / sanitize_project_path(cwd) / f"{session_id}.jsonl"`. The snapshot doesn't know about a session until the next `refresh()`, so it would leave brand-new sessions blank. If the file isn't at the sanitized path, fall back to one `*/<session_id>.jsonl` glob and memoize the result. A session with no findable transcript shows `--`.

**3. Context is the latest real main-thread turn's `input + cache_read + cache_creation`.** A "real" turn is `type == "assistant"`, not `isSidechain`, model not `<synthetic>`, total > 0, de-duplicated by `message.id` (last line wins). *Alternative:* sum `cost-state.modelUsage` — rejected: it's cumulative over the whole session and only written at exit.

**4. Tail-read with a growing window, cached by file stat.** Read backwards from EOF starting at 256 KB, doubling until N distinct real turns are found (N ≈ 24, enough for the sparkline) or the file start is reached; drop the first line when the window doesn't begin at byte 0 (likely cut mid-record). A fixed 256 KB window is not enough: tool results make lines large, and a window can hold only a handful of turns. Cache the result by `(path, size, mtime_ns)`, so an idle session costs one `stat`. Lines that fail to parse (e.g. a record still being appended) are skipped.

**5. The Live cell is text: `394k  ▲ +2.1k  ▁▂▂▃▅▆▇`.** Tokens are humanised (`394k`), growth is `ctx[last] − ctx[prev]`, and the sparkline uses block glyphs, so it drops into `col.write()` with no markup or CSS. The sparkline scales from 0 to the window's max rather than min-to-max, so a 390k→394k session reads as flat instead of a dramatic climb. Compaction shows up naturally as a drop; there is no special Live-row handling. The gauge reads the last assistant turn only and ignores `compactMetadata.postTokens`, because it's unclear what that figure covers (12.7k post-compaction vs a 57.7k first-turn floor in the sample). Between a compaction and the next turn the row therefore shows the pre-compaction size, which corrects itself on the next turn.

**6. Detail view: full parse on demand, exact-delta attribution.**
- Parsed when a row is opened (via the row's existing `on_click`), memoized by `(path, size, mtime_ns)`, and *not* re-parsed on the 2s tick. Transcripts reach ~10 MB, and a per-tick full parse would be the expensive path.
- Per-turn record: context, cache read, cache written, fresh input, output tokens, timestamp, and the `tool_use` names/hints of that turn. Compaction events are read from `compact_boundary` lines.
- A **cache miss** is a turn (other than the first) that wrote more than it read. On the sample this flagged one turn that wrote 168k and read 41k, and no others.
- **What filled the context**: the context delta arriving at turn *t* is attributed to the first tool called in turn *t−1* (or to "prompt / text" if there was none). Within a segment (session start, or since the last compaction), `floor + Σ positive deltas` equals the latest context exactly — on the sample, 57.7k + 372.3k = 430.0k. Top single-turn increases are listed with tool name and a short hint (path/command).
- *Alternative rejected:* attributing by transcript character counts. On the largest sample session it estimated ~1.16M tokens against a real 430k (screenshots and JSON escaping inflate it), so it can't be trusted even proportionally.

**7. Tests are pure-function tests on synthetic jsonl,** following the repo's one-file-per-module layout (`tests/test_claude_context.py`), with `claude_db.projects_dir` monkeypatched to `tmp_path` like the existing `isolated_db` fixture. Cases to cover: multi-block de-duplication, `<synthetic>`/zero-usage skipped, a partial trailing line, window-doubling to reach N turns, compaction segmenting, and the reconciliation invariant.

## Risks / Trade-offs

- [The transcript format is internal to Claude Code and can change (`usage` fields, `isSidechain`, `compact_boundary`)] → Parse defensively: skip malformed lines and missing fields, degrade to `--` instead of raising.
- [Attribution is approximate at the edges] → Parallel tool calls in one turn are lumped under the first tool; the delta also includes the previous turn's output tokens. Both are small next to tool-result sizes, and the reconciliation invariant still holds exactly.
- [Context covers the main thread only] → Correct for "how full is my context" (subagents have their own contexts), but the number won't line up with `cost-state` totals, which include subagents.
- [N tail reads every 2s scale with live session count] → About 1 ms each, and unchanged transcripts are served from the stat-keyed cache.
- [Sanitized-path mismatch for unusual `cwd` characters] → Glob fallback plus memoization; worst case the row shows `--`.
- [Compaction lag] → Between a compaction and the next assistant turn the Live row shows the old size. Accepted, since it self-corrects on the next turn.

## Open Questions

- Whether the detail view is an inline panel below the table or an `st.dialog`. Either satisfies the specs and tasks. Worth checking during implementation whether a dialog survives the Live fragment's 2s reruns.
