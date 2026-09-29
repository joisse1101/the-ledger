## Context

See proposal.md for motivation. Relevant current state:

- `claude_db._scan_transcript_file` computes `cost` by summing `_message_cost(model, usage)` over
  every deduped assistant turn, priced against the hardcoded `_MODEL_PRICING` table. Confirmed gaps:
  `claude-opus-5-5` isn't a table key at all; `claude-haiku-4-5-20251001` doesn't match the table's
  undated `claude-haiku-4-5` key. An unmatched model's usage is silently dropped (`_message_cost`
  returns `None`, contributing `0.0`), not flagged.
- Claude Code itself writes periodic `{"type": "cost-state", "totalCostUSD": ..., "modelUsage": {...},
  "hasUnknownModelCost": ...}` lines into the same transcript file. Traced empirically:
  - 173/177 locally scanned transcripts have at least one; 47 have several. Confirmed monotonically
    non-decreasing within a session, i.e. `totalCostUSD` is a running cumulative total, not a
    per-snapshot delta.
  - The 4 without one include a still-live session (57 assistant turns in, no `cost-state` yet) and
    two other same-Claude-Code-version sessions with 115-164 real assistant turns and no `cost-state`
    line at all - so its absence isn't limited to trivial/aborted sessions and can't be waited out
    reliably.
  - `cost-state` lines have no `timestamp` field; only file order indicates recency.
- Confirmed subagent inclusion: traced one session with an `Agent` tool launch. Summing that
  session's own visible assistant turns (today's method) reached $0.2285; its `cost-state` line
  reported $0.3372 - a $0.109 sonnet-5 gap (matching the subagent's `resolvedModel`) plus a small
  haiku charge that appears in `cost-state`'s `modelUsage` but nowhere in the parent transcript's own
  message lines. A subagent's own transcript is written to a per-session temp scratch directory
  outside `~/.claude/projects/` (the only tree `claude_db.py` scans) and isn't durably retained, so no
  amount of per-message re-scanning of `~/.claude/projects/*/*.jsonl` can ever recover that spend -
  `cost-state` is the only available source for it.
- Cost is stored per-transcript as one scalar (`ClaudeTranscript.cost`), in both `ledger.db` (wiped
  and rebuilt every server start) and the durable `history.db` (never wiped, shared schema via
  `_ensure_history_schema()`). Nothing downstream needs per-turn cost - `claude_context.py`'s detail
  view breaks down context growth per turn, never cost.

## Goals / Non-Goals

**Goals:**
- Use Claude Code's own `cost-state` figure as a session's cost whenever the transcript has one,
  eliminating the hand-maintained pricing table as a source of silent zeros for known-good sessions.
- Preserve today's per-message computation as a fallback for the transcripts that have no
  `cost-state` line, clearly labeled as an estimate rather than presented with equal confidence.
- Make the exact/estimated distinction visible in the UI (asterisk + tooltip) everywhere a session
  cost is shown, per the web-dashboard spec delta.

**Non-Goals:**
- Backfilling every historical `history.db` row with a recomputed exact cost. A row only improves
  when its source `.jsonl` still exists on disk and gets rescanned (a live `refresh()` or a
  `backup_history.py` run); a session already pruned from disk keeps whatever cost it was last given.
- Per-turn cost breakdown anywhere in the UI. `cost-state` is a cumulative snapshot, not a per-turn
  ledger, and nothing currently needs turn-level cost.
- Re-deriving `cost-state`'s own math (cache tiers, per-model rates). It's taken as-is; only the
  fallback path keeps `_MODEL_PRICING` and its multipliers.

## Decisions

**Cost source priority: last `cost-state` line, else the existing per-message estimate.**
`cost-state` lines have no timestamp, so "last" means last encountered during the existing
single-pass linear scan of the file - no second pass or explicit ordering logic needed, since JSONL
is already append-ordered. Alternative considered: average or sum multiple `cost-state` snapshots -
rejected, since the field is already cumulative and the last one is the total.

**A `cost-state` line with `hasUnknownModelCost: true` is still treated as `estimated`, not `exact`.**
Claude Code itself is flagging that it couldn't price part of the session; presenting that as an
unqualified exact figure would just relocate today's silent-gap problem one layer up instead of
fixing it. Alternative considered: always trust `cost-state` when present regardless of this flag -
rejected as reintroducing an unmarked estimate.

**New `cost_source: "exact" | "estimated"` field travels alongside `cost` everywhere the value does.**
`ClaudeTranscript` dataclass, both SQLite schemas (`ledger.db` and `history.db`), `fetch_transcripts()`'s
live/history merge, the `/api/transcripts` and `/api/sessions/{id}` payloads, and
`overview_stats.py`'s extreme-figure annotations (`_with_session` already carries `project`/
`session_id` for extremes; it gains this field the same way). Alternative considered: a boolean
`cost_is_estimated` - rejected only for symmetry with a possible future third source; either works,
this just reads slightly better next to `hasUnknownModelCost`-style naming already used in the raw
data.

**`history.db` migration: add the column with `DEFAULT 'estimated'`.**
Existing rows predate this change and can't be retroactively classified without their source
`.jsonl` (many are pruned by design - that's the point of `history.db`). Marking them `estimated` is
the conservative choice: it undersells sessions that happened to be fully-priced under the old
method rather than falsely marking a silently-zeroed one as trustworthy. `ledger.db` needs no
migration - it's dropped and rebuilt from scratch on every server start already.

**No change to `_MODEL_PRICING`'s role in the fallback path.** It keeps today's known-model
limitation, but only for the shrinking set of transcripts with no `cost-state` line at all (an
in-progress session, or one from a Claude Code build that predates `cost-state`). It stops being the
primary source of truth for cost, which is the actual fix.

**The estimate tooltip names the specific model id(s) `_MODEL_PRICING` didn't recognize, when any were
found during the fallback per-message scan.** Added after initial implementation, at the user's
request, to make "estimated" actionable rather than just a disclaimer - seeing `claude-opus-5-5` named
tells you exactly what to add to `_MODEL_PRICING` to get an exact figure next scan. A new
`unpriced_models: list[str]` field (sorted, de-duplicated model ids) travels alongside `cost_source`
through the same places: `_scan_transcript_file` collects it whenever `_message_cost` returns `None`
for a turn; `ClaudeTranscript`, both SQLite schemas (stored as a JSON-encoded string column, since
SQLite has no native array type), `fetch_transcripts()`'s merge, the `/api/transcripts` and
`/api/sessions/{id}` payloads, and `overview_stats.py`'s extreme-figure annotations all carry it the
same way `cost_source` does. It's populated regardless of the session's final `cost_source` (a
`cost-state` line can itself set `hasUnknownModelCost` without this app's own pricing table having
found anything to name), but the frontend only reads it on an `estimated` session. When it's empty on
an `estimated` session, the tooltip falls back to a generic message - this covers a `cost-state` line
present with `hasUnknownModelCost: true` but no unrecognized model in the *local* per-message scan
(e.g. a subagent's own model, invisible to this transcript's lines at all) and the case of no
`cost-state` line and no unrecognized model either (a session still in progress). Alternative
considered: only ever show the generic message - rejected, since naming the model is strictly more
useful whenever this app's own table is the reason, and costs nothing extra to compute since the scan
already calls `_message_cost` per turn.

## Risks / Trade-offs

- [Subagent inclusion is confirmed from one traced session, not exhaustively] -> Mitigation: this
  design trusts Claude Code's own reported total rather than re-deriving it, so correctness here
  rides on Claude Code's own accounting, not on this app's ability to model every subagent path. The
  `hasUnknownModelCost` fallback-to-estimated rule bounds the downside if that trust is ever wrong.
- [`cost-state` lags on long-running/live sessions - confirmed one session with 57 turns and no line
  yet] -> Mitigation: falls back to the per-message estimate (marked as such) until the next
  `refresh()`/`backup_history.py` pass picks up a `cost-state` line that has since appeared;
  self-corrects, no manual action needed.
- [Overview KPIs and cost-based chart shares will visibly jump once previously-zeroed sessions get
  real numbers] -> Accepted by the user; not a regression, the old figures were wrong.
- [A pruned-from-disk `history.db` row can never be upgraded from `estimated` to `exact`] ->
  Accepted as a Non-Goal; matches how `history.db` already accepts staleness in exchange for
  surviving Claude Code's own retention window.

## Migration Plan

1. Extend `_ensure_history_schema()`'s shared table definition with `cost_source TEXT NOT NULL
   DEFAULT 'estimated'`, applied via `ALTER TABLE ... ADD COLUMN` for `history.db` (never recreated)
   and as part of the `CREATE TABLE` for `ledger.db` (recreated every start regardless).
2. Update `_scan_transcript_file` to record the last `cost-state` line's `totalCostUSD` and
   `hasUnknownModelCost` alongside the existing per-message accumulation, and pick `cost`/
   `cost_source` per the priority above after the scan completes.
3. Thread `cost_source` through `ClaudeTranscript`, `fetch_transcripts()`'s merge, the two affected
   API responses, and `overview_stats.py`'s extreme annotations.
4. Frontend: add `cost_source` to `types.ts`, render the asterisk + tooltip in the All list's cost
   column, the session detail recap, and Overview's most-expensive/cheapest disclosures.
5. No rollback complexity beyond reverting the change - `ledger.db` rebuilds from scratch on next
   start either way, and `history.db`'s new column is additive (a rollback simply stops reading it).
