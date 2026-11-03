# Frontend: shared components

This page explains the components and helpers shared across pages: the responsive list, `ButtonSelector`, `ConfirmDialog` and the formatting functions. Read it before changing them.

> Requirements live in `openspec/specs/responsive-layout/spec.md`. This page describes how the code meets them, not what it must do.

## Responsive list (`components/list/`)

`ResponsiveList` picks `ListTable` (medium and wide) or `ListCards` (narrow) by viewport. Only one is ever mounted, and both take the same `columns`, `rows`, `rowId` and `onSelect`, so switching layouts never changes what is shown or its order.

A `ListColumn` carries these settings:

- `priority`, the table setting: `"high"` is shown at medium and up, `"low"` only at wide.
- `cardPriority`, set independently for the narrow card layout: `"primary"`, `"secondary"` or `"hidden"`. It defaults from `priority` when omitted.
- `sortKey`, optional, which makes `ListTable`'s header clickable and sortable.

Cards have no headers, so on narrow screens `AllList` offers a "Sort by" `<select>` instead.

## `ButtonSelector`

Files: `web/src/components/ButtonSelector.tsx` and its `.module.css`.

`ButtonSelector` is a controlled row of toggle buttons (`value`/`onChange`, generic over string or number values). It is single-select by default, as a radio group with `onChange(value)`. With `multiple` it uses toggle buttons, and `value` and `onChange` are arrays. It has no form binding, because this app has no forms.

### Narrow screens

On a narrow screen it scrolls sideways inside its own box. `web/src/hooks/useCanSideScroll.ts` fades whichever edge has more to reveal, using a CSS mask on the scroller driven by `data-fade-start` and `data-fade-end`.

### Look

The look is the ui-library's `.btn.btn-option`: joined segments with only the outer corners rounded, via `--radius-md` in `tokens.css`, at the app's `--tap` height. The scroller's padding and matching negative margin (`--glow-room`, no fixed `width`) exist so its clipping does not cut off the focus ring and hover glow.

### Tests

`test-setup.ts` stubs `ResizeObserver` since jsdom lacks it.

## `ConfirmDialog`

Files: `web/src/components/ConfirmDialog.tsx` and its `.module.css`.

`ConfirmDialog` is a small generic confirmation modal on a native `<dialog>`. It is kept mounted and synced to `open` (`showModal()`/`close()`), like `SessionDialog` but not full-screen on narrow viewports. Sessions' inline `DeleteControls` still confirms inline.

Its props are:

- `open`
- `title`
- `children`
- `confirmLabel`
- `pending`
- `error`
- `onConfirm`
- `onCancel`

While `pending`, both buttons are disabled and Esc and backdrop clicks are ignored. Otherwise all three call `onCancel`.

`test-setup.ts` stubs `showModal` and `close` where jsdom lacks them. Tests therefore cannot check native behavior such as focus trapping, and that is verified by hand.

## Formatting helpers

`web/src/lib/format.ts` holds display formatting for API values:

- `formatTime`
- `formatDateTime`
- `formatCost`
- `formatContext`
- `formatText`
- `formatCount`

Every one renders `"--"` for a missing value.

`web/src/lib/tokens.ts` holds `humanizeTokens` and `formatGrowth`. They are a deliberate port of `api/app/domain/context/formatting.py`'s `humanise_tokens` and `format_growth`, so the two languages agree on what a context figure reads as. The API already sends a ready-made `label` string for the Live list from the Python formatter directly. These functions are for the raw numbers the API sends elsewhere: the All list's Context column and the detail view's "Current context" figure.
