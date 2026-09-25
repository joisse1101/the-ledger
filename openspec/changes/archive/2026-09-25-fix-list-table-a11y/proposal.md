## Why

`ListTable` (used by the Live, All and Projects lists) has two accessibility defects that make it
misbehave with screen readers: `aria-sort` sits on the sort `<button>` where the ARIA spec doesn't
allow it, and each row is a `<tr role="button">`, which replaces the row's table semantics. Found
while comparing the custom tables against TanStack Table; neither defect depends on a library, so
they can be fixed in place.

## What Changes

- Move `aria-sort` from the inner sort `<button>` to its `<th>`, so a sorted column's direction is
  announced. Unsorted sortable columns keep `aria-sort="none"`; non-sortable columns get none.
- Stop using `role="button"` / `tabIndex` / `onKeyDown` on `<tr>`. Rows keep their `onClick` (mouse
  users can still click anywhere on a row) and keep `data-row-id`, but the keyboard/screen-reader
  entry point becomes a real `<button>` wrapping the first visible cell's content, which calls
  `onSelect`. It stops propagation so the row's click handler doesn't fire a second time.
- CSS: reset the in-cell button so it looks like plain cell text, and give it a visible
  `:focus-visible` ring (the row-level focus styling no longer applies).
- Give the Projects list's button an accessible name that says activating it starts a delete
  (a row there is a delete trigger, not a detail view), e.g. "Select project <name> to delete".
  Live rows may fold their pending-decision text into the label; decide during implementation.
- `ListCards` is unchanged: a real `<button>` per card is already the correct pattern.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No agreed requirement in `openspec/specs/` covers list keyboard/screen-reader semantics
(searched `web-dashboard`, `responsive-layout` and the rest), so no delta spec is needed. This
change brings the markup in line with standard ARIA table semantics without altering any specified
behavior.

## Impact

- `web/src/components/list/ListTable.tsx` — header and row markup.
- `web/src/styles/sessions.css` — in-cell button reset and focus ring.
- `web/src/components/projects/ProjectsList.tsx` (and possibly `LiveList.tsx`) — accessible name for
  the row button.
- `web/src/components/list/ResponsiveList.test.tsx` — existing tests keep passing unchanged; add
  cases for `aria-sort` on the `<th>` and for keyboard activation via the row's button.
- No API, dependency, or data changes. `ListCards` and the three static `detail-table`s in
  `SessionDialog` are untouched.
