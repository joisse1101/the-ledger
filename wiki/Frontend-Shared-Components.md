# Frontend: shared components

> Requirements live in `openspec/specs/responsive-layout/spec.md`. This page describes how the code meets them, not what it must do.

- **Responsive list** (`components/list/`): `ResponsiveList` picks `ListTable` (medium/wide) or
  `ListCards` (narrow) by viewport — only one is ever mounted, both take the same `columns`/`rows`/
  `rowId`/`onSelect`, so switching layouts never changes what's shown or its order. A `ListColumn`
  carries a table `priority` (`"high"` shown at medium+, `"low"` only at wide) and an independent
  `cardPriority` (`"primary"`/`"secondary"`/`"hidden"`, defaulted from `priority` when omitted) for
  the narrow card layout, plus an optional `sortKey` that makes `ListTable`'s header (or `AllList`'s
  narrow-screen "Sort by" `<select>`, since cards have no headers) clickable/sortable.

- **`ButtonSelector`** (`web/src/components/ButtonSelector.tsx` + `.module.css`): a controlled row of toggle
  buttons (`value`/`onChange`, generic over string/number values) — single-select by default (radio
  group, `onChange(value)`), or `multiple` (toggle buttons, `value`/`onChange` are arrays). On a narrow
  screen it scrolls sideways inside its own box, and `web/src/hooks/useCanSideScroll.ts` fades whichever edge has
  more to reveal (a CSS mask on the scroller, driven by `data-fade-start`/`data-fade-end`). The
  look is the ui-library's `.btn.btn-option` (joined segments, only the outer corners rounded, via
  `--radius-md` in `tokens.css`) at the app's `--tap` height. The scroller's padding and matching
  negative margin (`--glow-room`, no fixed `width`) exist so its clipping doesn't cut off the focus
  ring and hover glow. No form binding: this app has no forms. `test-setup.ts` stubs `ResizeObserver` since jsdom lacks it.

- **`ConfirmDialog`** (`web/src/components/ConfirmDialog.tsx` + `.module.css`): a small generic confirmation
  modal on a native `<dialog>` kept mounted and synced to `open` (`showModal()`/`close()`, like
  `SessionDialog`, but not full-screen on narrow viewports). Props: `open`, `title`, `children`,
  `confirmLabel`, `pending`, `error`, `onConfirm`, `onCancel`. While `pending`, both buttons are
  disabled and Esc/backdrop clicks are ignored; otherwise all three call `onCancel`. `test-setup.ts`
  stubs `showModal`/`close` where jsdom lacks them, so tests can't check native behavior such as
  focus trapping — that's verified by hand. Sessions' inline `DeleteControls` still confirms inline.
- **`web/src/lib/format.ts`** — display formatting for API values (`formatTime`, `formatDateTime`,
  `formatCost`, `formatContext`, `formatText`, `formatCount`; every one renders `"--"` for a missing
  value). **`web/src/lib/tokens.ts`** — `humanizeTokens`/`formatGrowth`, a deliberate port of
  `claude_context.py`'s `humanise_tokens`/`format_growth` so the two languages agree on what a
  context figure reads as (the API already sends a ready-made `label` string for the Live list from
  the Python formatter directly; these are for the raw numbers the API sends elsewhere — the All
  list's Context column, the detail view's "Current context" figure).
