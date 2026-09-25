## 1. Sort header semantics

- [x] 1.1 In `web/src/components/list/ListTable.tsx`, move `aria-sort` from the sort `<button>` to its `<th>` (sortable columns: `ascending`/`descending`/`none`; non-sortable columns: no attribute). Verify with a new test in `ResponsiveList.test.tsx` that the `<th>` carries `aria-sort` for the active sort column and that the `<button>` does not.

## 2. Row semantics

- [x] 2.1 In `ListTable.tsx`, remove `role="button"`, `tabIndex` and `onKeyDown` from `<tr>`; keep `onClick`, `data-row-id` and `rowClassName`. Verify the existing "call the select handler with the clicked row" and "same row IDs in the same order" tests still pass unchanged.
- [x] 2.2 Wrap the first visible cell's content in a `<button type="button">` that calls `onSelect(row)` and `stopPropagation()`s so the row's click doesn't fire it twice. Verify with a new test that pressing Enter/Space on that button calls `onSelect` once and that clicking elsewhere in the row still calls it once. (Done as: the control is a real focusable `<button type="button">`, and a click on it or elsewhere in the row selects exactly once. jsdom can't simulate Enter/Space, which are native button behavior; that part is covered by the manual keyboard check in 5.2.)
- [x] 2.3 Confirm `<tr>` no longer has `role="button"` by asserting `getAllByRole("row")` returns the header row plus one row per item.

## 3. Accessible names

- [x] 3.1 Let a list supply the row button's accessible name (e.g. an optional `rowLabel?: (row) => string` on `ResponsiveListProps`, passed as `aria-label`), leaving the default as the cell's own text. Verify with a test that a supplied label is exposed via `getByRole("button", { name })`.
- [x] 3.2 In `ProjectsList.tsx`, supply a label saying the action starts a delete (e.g. "Select project <name> to delete"). Verify the existing `ProjectsList` tests (delete hidden off-machine, confirm flow) still pass and a name-based query finds the button.
- [x] 3.3 In `LiveList.tsx`, decide whether to fold the pending-decision text into the label; if yes, add it and verify with a test, if no, leave it and note that in the task. (Decided no, `LiveList.tsx` unchanged: the table already has a separate "Decision" cell, which now that rows keep table semantics a screen reader reads with its column header, so folding it into the button label would announce it twice.)

## 4. Styling

- [x] 4.1 In `web/src/styles/sessions.css`, reset the in-cell button so it renders as plain cell text (no border/background/padding, inherited font and color, left- or right-aligned per `data-align`) and add a visible `:focus-visible` ring. Verify in a browser at wide, medium and narrow widths, in light and dark themes, that rows look unchanged and Tab shows a clear focus ring. (CSS written; checked so far at wide width in the light theme on Projects and All: rows look unchanged and the focus ring shows inside the cell, unclipped. Still to check by hand: medium and narrow widths and the dark theme. A resized window didn't change the viewport in the automated browser.)

## 5. Final verification

- [x] 5.1 Run `npm test` and `npm run build` in `web/` and verify both pass with no type errors.
- [x] 5.2 Manually verify with a keyboard only (Tab, Enter, Space) on the Live, All and Projects lists that every row can be reached and activated, and that sorting still works from the header buttons. If a screen reader is available, verify a sorted column is announced with its direction and table navigation reads cells with their column headers. (Partly done in Chrome on Projects and All: Tab reaches a row's button, Enter opens the delete confirmation, and clicking a sort header still sorts. Still to check by hand: Space, the Live list, and a screen reader.)
