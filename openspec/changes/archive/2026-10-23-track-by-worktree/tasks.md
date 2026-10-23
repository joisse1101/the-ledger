## 1. Worktree path rule

- [x] 1.1 Add `api/app/core/worktrees.py` with `Worktree(repo_root, name)` and `parse_worktree(cwd)` (design D1), and `api/tests/core/test_worktrees.py` covering a Windows path, a POSIX path, a subfolder of a worktree, a name containing `+`, a plain repo path (`None`), an empty string, and a path that merely contains `worktrees` without `.claude`; verify `pytest tests/core/test_worktrees.py` passes
- [x] 1.2 Verify `pytest tests/test_layers.py` still passes with the new module imported from `repositories` and `domain`

## 2. Scan, schema and history migration

- [x] 2.1 In `scanner._scan_transcript_file`, keep the first `cwd` seen, and for a worktree session set `worktree` to its name and `project` to the repo root's basename (design D2, D3); add scanner tests (worktree session, `cd` into a subfolder, `cd` out of the worktree, ordinary session) and verify they pass
- [x] 2.2 Add `worktree TEXT NOT NULL DEFAULT ''` to `ensure_history_schema` (table and in-place `ALTER`), and to the insert in `snapshot.refresh` and the upsert in `history.py`; verify a fresh `ledger.db` and a pre-existing `history.db` fixture both end up with the column
- [x] 2.3 Add the idempotent history correction pass from design D4 (rows with empty `worktree` and a worktree `cwd` get `worktree` and `project` set, pruned rows included); verify a test runs it twice on a legacy-shaped fixture and the second run changes nothing
- [x] 2.4 Add `worktree` to `ClaudeTranscript`, `_row_to_transcript` and a `project_folder` helper (design D3); verify `tests/repositories/test_claude_transcripts.py` covers a worktree row and a plain row

## 3. Project membership and delete

- [x] 3.1 Make `overview_stats.filter_by_project` match on `project_folder`; verify `test_overview_stats.py` shows a worktree session counted for its repo's folder, not for a same-named other project, and that same-named folders are still not merged
- [x] 3.2 Make `queries.transcript_paths_for_project` and the row-delete helpers match the same rule, and make `claude_transcripts.delete_project_transcripts` remove every folder holding a member transcript (design D8); verify tests that deleting a project removes its worktree sessions' files and rows from both `ledger.db` and `history.db`, and leaves another project's worktree sessions alone
- [x] 3.3 Verify against the real data shape: run the scan over a temp `~/.claude/projects/` fixture mirroring the observed `add-wiki-docs` / `api` / `the-ledger` rows and check all three resolve to project `the-ledger`

## 4. Work-stream grouping and summary (API)

- [x] 4.1 Add `GROUP_KEYS["worktree"]` (`wt <name>`, else branch, else `(no branch)`) and `worktrees` in `summary()`; verify `test_overview_stats.py` covers worktree-over-branch, a worktree session that switched branches, a branch and a worktree with the same name staying separate, the 7-slice fold with mixed streams, and the summary counts
- [x] 4.2 Accept `worktree` in the overview route's `group_by` validation (`overview_service`) and the response schema; verify an API test for `group_by=worktree` and that `group_by=branch` output is unchanged

## 5. Sessions list (API)

- [x] 5.1 Add `worktree` to `transcript_item`, `SORT_FIELDS` and the router's `SortField`; add the `worktree` query parameter through `transcript_service` and `filter_transcripts`; add `worktrees` to the options payload; verify `test_transcript_query.py` and an API test cover filter, sort (blank last) and options, with filters still combining with AND

## 6. Frontend

- [x] 6.1 Update `web/src/api/types.ts` and `queries.ts`: `worktree` on the transcript, `worktrees` in options and in the summary, `"worktree"` in `OverviewGroupBy`, the sort field, and the `worktree` filter parameter; verify `npm run build` type-checks and `queries.test.tsx` asserts the parameter is sent
- [x] 6.2 Add `"worktree"` to `GroupLabel` in `chartTheme.ts` and word headings, aria labels and tooltips for it ("branch / worktree"); verify the `GroupDonutChart` and `GroupBarChart` tests render the label and that a `wt ` entry and a branch entry get different colours
- [x] 6.3 Switch `ProjectDetailPanel` to `groupBy: "worktree"` and the new label, and add a Worktrees figure beside Branches in `ProjectSummaryStats`; verify `ProjectDetailPanel.test.tsx` asserts the request and the figure
- [x] 6.4 Add the Worktree column, sort and `FilterMultiselect` filter to `AllList`; verify `AllList` tests cover the filter reaching the request, `--` for a session with no worktree, and the Branch column still showing the branch

## 7. Documentation

- [x] 7.1 Update the wiki pages: Backend-Data-Layer (column, `project_folder`, path rule), Backend-History-Store (column and correction pass), Backend-API-Routes (`worktree` parameter, `group_by`), Backend-Overview-And-Queries (group key, summary, membership), Frontend-Overview, Frontend-Projects, Frontend-Sessions, and Testing (new test files); verify `cd api; python check_docs.py` passes

## 8. Integration

- [x] 8.1 Run `cd api; pytest`, `cd web; npm test` and `cd web; npm run build`; verify all pass
- [x] 8.2 Start the app (`.\Start-Ledger.ps1`) against the real `~/.claude` data and verify in the browser: The Ledger's panel shows `wt add-wiki-docs` and `wt skills-and-agents` entries, no `add-wiki-docs` or `api` project appears on Overview or in the All list's Project filter, and the Worktree filter lists both
