## Why

Session cost is silently wrong today. `claude_db.py` recomputes every session's cost by hand from
raw per-message `usage` fields, priced against a hardcoded `_MODEL_PRICING` table matched by exact
model-id string. Any model not in that table (confirmed: `claude-opus-5-5`, which isn't a table key
at all, and `claude-haiku-4-5-20251001`, whose date-suffixed id doesn't match the table's
undated `claude-haiku-4-5`) has its usage silently dropped rather than priced — a session that spent
$3.34 on `claude-opus-5-5` per Claude Code's own tracking shows as **$0.00** in the ledger. The table
will keep drifting every time Anthropic ships a model id, so this isn't a one-time fix.

Separately, this recompute can never see async-subagent spend at all: an `Agent` tool call's own
transcript is written to a temp scratch directory outside `~/.claude/projects/` (the only tree
`claude_db.py` scans) and isn't durably retained, so a session that spawned subagents undercounts its
own cost even when every model it used is priced correctly. A traced example confirmed this: a
session's own `cost-state` line (Claude Code's own running cost tracker, already present in the
transcript) totaled $0.3372, while summing that same session's own visible assistant turns only
reached $0.2285 - a $0.109 gap matching the subagent's `resolvedModel`, plus a small haiku charge that
never appears in the parent transcript's message lines at all.

## What Changes

- Prefer the transcript's own `cost-state` line (Claude Code's own cumulative, Anthropic-priced,
  subagent-inclusive cost tracker) as a session's cost, using the last such line when a transcript
  has more than one.
- Fall back to today's per-message recompute only for a transcript with no `cost-state` line at all
  (an in-progress session Claude Code hasn't snapshotted yet, or one from before `cost-state`
  existed) - kept as a best-effort estimate, not removed.
- Track and expose which source produced a session's cost (`exact` vs `estimated`), so the UI can
  tell them apart instead of presenting every figure with equal confidence.
- Mark an estimated cost with a visible asterisk everywhere a session's cost is shown (the All
  sessions list, the session detail recap, and any Overview figure derived from an estimated
  session), with a tooltip explaining that it's a best-effort figure computed only from the models
  this app recognizes and only from the session's own main-thread turns, excluding any subagent
  spend.
- No change to `_MODEL_PRICING`'s role as the fallback estimator's pricing source - it keeps its
  existing known-model limitation for that fallback path only.

## Capabilities

### Modified Capabilities
- `web-dashboard`: cost figures (Overview summary figures, the All sessions list's cost column, and
  the session detail recap's estimated cost) must distinguish an exact, Claude-Code-reported cost
  from a best-effort estimate, marking the latter with an asterisk and an explanatory tooltip.

## Impact

- `api/claude_db.py`: `_scan_transcript_file`/`_message_cost` (read `cost-state` lines, keep the
  existing per-message math as fallback only), the `ClaudeTranscript` dataclass and its DB schema
  (new cost-source field), `fetch_transcripts()`'s live/history merge (must carry the new field
  through).
- `api/overview_stats.py`: KPI/extreme figures and cost-based chart shares will shift once real
  numbers replace silently-zeroed ones for affected sessions; no aggregation logic changes, but any
  session-level "is this estimated" flag needs to reach the figures that can be marked as
  estimate-derived.
- `api/transcript_query.py` / `GET /api/transcripts`, `GET /api/sessions/{id}`: response shape gains
  the cost-source field per session.
- `web/src/api/types.ts`, `web/src/lib/format.ts` (or a new cost-formatting helper), the All list's
  cost column, `SessionDialog`'s recap, and `SummaryStats`/extreme-figure disclosures on Overview:
  render the asterisk and tooltip wherever a cost is estimated.
- Existing tests covering cost (`test_claude_db.py`, `test_claude_transcripts.py`,
  `test_overview_stats.py`, `test_api_data.py`, `test_transcript_query.py`, and frontend tests
  touching cost display) need fixtures/assertions updated for the new source-tagged cost.
