## 1. Backend: startup content and estimates

- [x] 1.1 Inspect the real `instructions`, `skill_listing`, `agent_listing_delta` and `mcp_instructions_delta` attachments (initial and later ones, including any removal fields) in `~/.claude/projects` and write down the exact shapes as fixtures in `api/tests/`; verify the fixtures parse with the existing `_scan` untouched
- [x] 1.2 Extend the `_scan` pass in `api/claude_context.py` to collect startup content events with their position (turn count at the time), tolerant of missing or odd fields; verify with tests for each attachment kind and for malformed entries being skipped
- [x] 1.3 Add pure functions that estimate items (`len/4`) and fold events into startup snapshots, applying additions and removals; verify with tests for a mid-session skill add, an agent removal, and a category with no content being absent
- [x] 1.4 Add per-response breakdown building: cumulative growth by tool per segment (reusing the `attribute_growth` rules), proportional scaling to the segment's first-response context, and a non-negative remainder; verify with tests that every response's rows sum to its context, including after a compaction and when estimates exceed the floor

## 2. Backend: API

- [x] 2.1 Add `breakdown` (snapshots and per-response rows) to `SessionDetail` and `_detail_json` in `api/server.py`, additive and failing soft (a breakdown error drops only the breakdown and logs the session id); verify with an API test on a fixture transcript and one with no startup content
- [x] 2.2 Update `api/tests` for the unchanged parts and run `cd api; pytest` to verify nothing else regressed

## 3. Frontend: types and chart

- [x] 3.1 Mirror the new fields in `web/src/api/types.ts` and add a small pure helper for per-category shares; verify with a Vitest unit test (24% example, rounding, zero context)
- [x] 3.2 In `TokensChart.tsx`, replace the bar tooltip with the compact category tooltip (top categories, tokens, share, estimates marked) and add click selection reporting the response number; verify with a unit test of the tooltip content builder and by hovering and clicking a bar in a real browser
- [x] 3.3 Add `ContextBreakdownPanel` rendered by `SessionDialog.tsx` under the chart: categories collapsed by default, expandable to items, estimate labels, dismiss control, replaced when another bar is selected; verify with component tests and by resizing a real browser to narrow width and tapping a bar

## 4. Docs and checks

- [x] 4.1 Update the wiki pages `Backend-Data-Layer`, `Backend-API-Routes`, `Frontend-Sessions` and `Testing` for the breakdown; verify `cd api; python check_docs.py` passes
- [x] 4.2 Run `cd web; npm test`, `cd web; npm run build` and `cd api; pytest`, and `openspec validate context-breakdown --strict`; verify all pass
