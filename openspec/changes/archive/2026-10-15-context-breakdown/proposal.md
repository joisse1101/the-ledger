## Why

The session detail modal can say how much a session's context grew and which tool caused it, but
the context a session starts with (memory files, skills, custom agents, MCP instructions, system
prompt) shows up as one opaque number: the first response's size. Claude Code's `/context` itemises
exactly that load, and a heavy startup load is often the biggest, most avoidable part of a large
context. The modal should show the same breakdown for every response, so the user can see what
filled the context at any point in the session.

## What Changes

- The transcript is the only source (`/context` output is not recorded in it), so the backend
  estimates each startup category from the content Claude Code records in the transcript: memory
  files, the skill listing, agent listings and MCP instructions, with later additions and removals
  applied. Sizes are estimates, labelled as approximate.
- Each response gets a breakdown that always adds up to that response's exact context size:
  estimated startup categories + exact cumulative growth by tool since the segment started + a
  remainder row ("Everything else": system prompt, built-in tools, compaction summary).
- Hovering a bar in the "Tokens per response" chart shows a compact tooltip: the response's
  context and its largest categories, each with tokens and its share of that response's context.
- Clicking or tapping a bar pins a panel under the chart with every category for that response;
  each category expands to its items (each memory file, skill, agent, MCP server). Collapsed by
  default.
- **Modified requirement:** "Only absolute token counts are shown" now allows a category's share of
  *that response's own context*; percentages of a context window, limits and thresholds stay banned.
- The existing "What filled the context" section is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `live-context-gauge`: adds the per-response context breakdown (estimated startup categories,
  exact growth by tool, remainder), its hover and pinned views, and a requirement that estimated
  figures are labelled approximate; narrows "Only absolute token counts are shown" to permit
  shares of a response's own context.

## Impact

- `api/claude_context.py`: parse the startup-content attachments during the existing transcript
  scan; build per-response breakdowns.
- `api/server.py`: the session detail JSON gains the breakdown data (additive).
- `web/src/api/types.ts`: mirror the new fields.
- `web/src/components/sessions/TokensChart.tsx` and `SessionDialog.tsx`: bar tooltip, bar
  selection, pinned panel.
- Tests in `api/tests/test_claude_context.py` and the web Vitest suite.
- Wiki: `Backend-Data-Layer`, `Backend-API-Routes`, `Frontend-Sessions`, `Testing`.
- No new dependencies, no schema migration, no change to the Live table.
