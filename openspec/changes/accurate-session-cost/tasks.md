## 1. Data layer (`api/claude_db.py`)

- [x] 1.1 Extend `_ensure_history_schema()`'s shared table definition with `cost_source TEXT NOT NULL
      DEFAULT 'estimated'`, applied so it works both for `history.db`'s existing rows (via `ALTER
      TABLE ... ADD COLUMN`, since that file is never recreated) and for `ledger.db`'s `CREATE TABLE`
      (rebuilt every server start regardless); verify by inspecting both files' schemas after a
      backend start and a `backup_history.py` run.
- [x] 1.2 In `_scan_transcript_file`, while scanning lines, also record the last `type == "cost-state"`
      line's `totalCostUSD` and `hasUnknownModelCost`, alongside the existing per-message `cost`
      accumulation; verify with a fixture transcript containing one `cost-state` line and assert both
      values are captured.
- [x] 1.3 After the scan, set `cost`/`cost_source` per design.md's priority (last `cost-state` line
      when present and `hasUnknownModelCost` is false -> `("exact", totalCostUSD)`; otherwise the
      existing per-message sum -> `("estimated", sum)`); verify with fixtures covering: a
      `cost-state` present and clean, a `cost-state` present with `hasUnknownModelCost: true`, and no
      `cost-state` line at all.
- [x] 1.4 Add `cost_source` to the `ClaudeTranscript` dataclass, its `INSERT`/`SELECT` column lists for
      both `ledger.db` and `history.db`, and `fetch_transcripts()`'s live/history merge (the live row's
      `cost_source` wins the same way its `cost` already does); verify via `test_claude_db.py`.

## 2. API surface

- [x] 2.1 Add `cost_source` to the `/api/transcripts` item shape (`transcript_query.py`'s `Page`
      items) and the `/api/sessions/{id}` recap payload; verify via `test_transcript_query.py` and
      `test_api_data.py` assertions on the new field.
- [x] 2.2 Extend `overview_stats.py`'s extreme-figure annotation (`_with_session`, used for the
      most-expensive/cheapest KPIs) to also carry that session's `cost_source`; verify via
      `test_overview_stats.py`.

## 3. Frontend

- [ ] 3.1 Add `cost_source: "exact" | "estimated"` to the relevant shapes in `web/src/api/types.ts`.
- [ ] 3.2 Add a small cost-display helper (asterisk + tooltip text) alongside `lib/format.ts`'s
      `formatCost`, with the tooltip explaining the estimate covers only recognized models and only
      the session's own main-thread turns, excluding subagent spend; use it in the All list's cost
      column, `SessionDialog`'s recap cost, and Overview's most-expensive/cheapest disclosures; verify
      by rendering an estimated and an exact session in each location and confirming the mark only
      appears on the estimated one.

## 4. Tests and verification

- [ ] 4.1 Update `test_claude_db.py`/`test_claude_transcripts.py` fixtures and assertions for the new
      `cost_source` field and the `cost-state`-preferred computation.
- [ ] 4.2 Update `test_overview_stats.py` and `test_api_data.py` fixtures/assertions for the new field
      on extremes and on transcript/session responses.
- [ ] 4.3 Update frontend tests touching cost display (the All list, `SessionDialog`, Overview
      `SummaryStats`/extreme disclosures) to cover both the marked-estimate and unmarked-exact cases.
- [ ] 4.4 Run `pytest` in `api/` and `npm test` + `npm run build` in `web/`, and confirm they pass.
- [ ] 4.5 Manually verify against real data: run a refresh against the local Claude Code history and
      confirm the `the-ledger` session referenced in this change (`7819ee5e-675d-4a7f-a926-...`) now
      shows its `cost-state`-derived cost (~$3.34) with no asterisk, and that a session with no
      `cost-state` line shows its estimate with the asterisk and tooltip.
