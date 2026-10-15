## Context

`api/claude_context.py` already makes one pass over a session's transcript (`_scan`) and produces
`SessionDetail` (turns, compactions, tool attribution). `/api/sessions/{id}` serialises it
(`_detail_json` in `api/server.py`), `web/src/api/types.ts` mirrors it, and `TokensChart.tsx`
draws the stacked bars with Vega-Lite (default tooltips, no selection). See proposal.md for why.

Observed in real transcripts: `/context` output is not recorded, but `attachment` entries are:
`instructions` (memory files, with `path` and `content`), `skill_listing` (`content`, `names`,
`isInitial`), `agent_listing_delta` (`addedLines`, `removedTypes`, `isInitial`),
`mcp_instructions_delta` (`addedBlocks`, `removedNames`) and `deferred_tools_delta` (names only).
The system prompt and built-in tool schemas are not recorded anywhere. No tokenizer is available,
so every startup size is an estimate.

## Goals / Non-Goals

**Goals:**
- A per-response breakdown that always sums to the response's exact context.
- One implementation of the arithmetic, on the backend, so the browser only renders.
- Reuse the existing scan; no second read of the transcript.

**Non-Goals:**
- Exact startup sizes, a tokenizer, or capturing real `/context` output via a hook (possible
  later; the breakdown shape leaves room to replace estimates per session).
- Any change to the Live table, the "What filled the context" section, or cost/history code.
- Percentages of the model's context window (what `/context` shows, e.g. 0.7% of 1m). The
  transcript doesn't record the window size, so it would need a configured or guessed value, and a
  wrong one would make every percentage wrong. Shares are of the selected response's own context
  instead (e.g. 24%); this was a deliberate choice, not an omission.

## Decisions

**1. Estimate with `len(text) / 4` per item, then scale to fit.** Cheap, deterministic, no
dependency. Per segment: if the category estimates sum to more than the segment's first-response
context, scale them all by `floor / sum`. The remainder is `floor - startup` (never estimated),
so rows always reconcile. *Alternative:* a tokenizer library: heavier, still not Claude's. *Alternative:*
show raw character counts: not comparable to the exact token figures around them.

**2. Backend builds the whole breakdown; the browser renders it.** The attribution rules (growth is
credited to the previous response's first tool) already live in `attribute_growth`; recomputing
cumulative growth in TypeScript would duplicate them and could drift (architecture rule: one
definition of a contract). The detail JSON gains `breakdown`, additive and backward-compatible.

**3. Send startup snapshots, not per-response item lists.** Startup content changes rarely, but
there can be hundreds of responses and 40+ skills. The payload is:
`breakdown.snapshots`: list of `{ position, categories: [{ name, tokens, items: [{label, tokens}] }] }`,
one per change in startup content (position = number of turns before it), plus
`breakdown.turns`: one `{ snapshot, growth: [{ tool, tokens }], remainder }` per response, where
`growth` is cumulative since the segment start. Items live only in snapshots. *Alternative:* full
categories on every turn, which multiplies item rows by turn count.

**4. Segments follow compactions.** Cumulative growth and the scaling `floor` restart at each
compaction's first response; the compaction summary lands in the remainder. Startup snapshots carry
across compactions (Claude Code reloads startup content), so a compaction does not clear them.

**5. Deltas: apply what the transcript records.** `instructions` and `skill_listing` replace or
extend their category from their `position`; agent and MCP deltas add and remove by name. Where an
attachment kind records no removals (to be confirmed against real transcripts at the start of
implementation), later entries only add. A category with no recorded content is omitted.

**6. Chart interaction in Vega-Lite.** Replace the bar layer's field tooltip with a custom
tooltip handler built from `breakdown.turns[i]` (top categories + shares, estimates marked), and
add a click selection on the bar layer that reports the response number to `SessionDialog` through
a callback prop. `SessionDialog` holds the selected response in state and renders a new
`ContextBreakdownPanel` under the chart: categories as a table with `<details>` per category for
items, collapsed by default, with a dismiss control. Percentages are `tokens / response context`.

**7. Failure isolation.** Building the breakdown is wrapped so that an unreadable or odd
attachment drops that category rather than the detail view (core principle: no silent failure, so
the skipped category is logged with the session id).

## Risks / Trade-offs

- [Estimates are crude (`chars/4`), and skills/agents are estimated from listing lines, not from
  their full definitions] → labelled approximate everywhere; scaled so they cannot exceed the exact
  total; remainder row names what it holds.
- [Attachment shapes may differ across Claude Code versions or lack removal info] → tolerant
  parsing, missing category = absent, fixtures cover old and new shapes; verify against real
  transcripts first (task 1.1).
- [Click selection on a Vega bar behaves differently on touch] → verify in a real browser at
  narrow width (no E2E harness here); the pinned panel does not depend on hover.
- [Payload growth on long sessions] → snapshots hold items once; per-turn rows hold only tool
  totals.
- [Click selection does not work on live sessions] → observed in use: hover works but click does not pin the panel while a session is live. A hypothesis (the chart being rebuilt on each poll, losing the click) was tried by swapping in a hidden replacement chart; it did not help and was discarded, and the cause is unknown. Accepted as a known limitation; not pursued further.
- [Spec rule on percentages is narrowed] → only shares of a response's own context are allowed;
  the Live table remains tokens-only and no window size appears anywhere.

## Migration Plan

Additive JSON field and additive UI; no stored data changes. Rollback is reverting the commit(s).
A session whose transcript lacks the new field's inputs renders as before plus a growth/remainder-only
breakdown.
