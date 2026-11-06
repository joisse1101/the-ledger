# Frontend: sessions

This page explains how the Live and All sessions pages are built, including the session detail dialog, delete and the tokens chart. Read it before changing them. A live session and Remote mode are defined in the [Glossary](Glossary.md#live-session).

> Requirements live in `openspec/specs/web-dashboard/spec.md`, `openspec/specs/remote-session-control/spec.md`. This page describes how the code meets them, not what it must do.

## Pages

Live and All are separate pages. Each keeps its selection in the URL (`?session=<id>`), so a reload or a shared link reopens the selection.

- `web/src/components/sessions/` holds the shared code.
- `web/src/pages/LiveSessionsPage.tsx` is Live, at `/`.
- `web/src/pages/SessionsPage.tsx` is All, at `/sessions`.

## Live

### The list

`LiveList` polls through `useLive`. It has its own "Auto-refresh" switch, and with the switch off the "Last refreshed" caption stays frozen.

Each row can carry two badges. `LiveList` badges a row (`pending-badge`) from `/api/live`'s `pending_decision`. It shows a **Should compact** (amber) or **Needs compact** (red) pill (`compact-badge`) from the row's `compact.state`, muted while the session is `idle`.

The Live list (not All) also gains an **Auto-approve** column that marks sessions with it on. The column appears only once `/api/meta.relay_hook_seen` is true, and on narrow cards it is a badge instead.

### The panel under the list

Selecting a row renders `LiveSessionPanel` under the list, not in a dialog. The panel holds `LiveControl`, a control-only view. The panel reads the Live list from the query cache with `auto: false`, so only `LiveList`'s switch drives polling.

### The pending prompt

`LiveControl` shows the session's oldest pending prompt, drawn by `DecisionPrompt`. A permission prompt offers Approve and Deny with an optional reason. An `AskUserQuestion` offers the real options, multi-select and free text. The prompt logic is in `web/src/lib/prompt.ts`.

`usePendingDecision` polls while it is mounted. If a prompt vanishes without this view having answered it, the view says the session already moved on instead of going blank, and a 409 says the same. It shows nothing on a non-local device while Remote mode is off.

`LiveControl` also has an "Open repo window" button (`useOpenRepo`) and a "Last auto-approved: tool at time" line.

### Auto-approve

`AutoApproveControl` sits beside the panel's title and is a per-session **Auto-approve** switch (`useSetAutoApprove`). It is a switch only on the machine running the app. On another device it is read-only "Auto-approve on" text. It is shown nowhere until `/api/meta.relay_hook_seen` is true.

### Remote mode control

`LiveList` carries `RemoteModeControl`. On the machine running the app (`is_local`) it is a switch. Elsewhere it is read-only text such as "Remote mode: on, 7h left".

The switch drives the whole of Remote mode through `POST /api/remote-mode`. It shows the starting step ("Starting Docker…") or the failure reason from `/api/meta.remote_mode`, and it stays checked while starting so it can cancel.

Once Remote mode is `ready`, a **Show QR** button opens `RemoteQrDialog`. The dialog uses `useRemoteQr`, which fetches `/api/remote-mode/qr` only while it is open. It shows the code and the address, never the token.

## All

`AllList` debounces its search box (`useDebouncedValue`, 300ms). It drives `Project`, `Version`, `Branch` and `Worktree` `FilterMultiselect`s from the API's option lists. A `FilterMultiselect` is a `<details>`-based checkbox list, so no popover or portal machinery is needed. The list pages 50 at a time through `useTranscripts`'s "Load more".

The table has 14 columns, so `AllList` carries a `sessions-all` class that tightens its cells: less padding, a 12ch cap on short columns, 18ch on `Project` and `Title`, and 20ch on the two time columns so a full timestamp shows. Other tables keep the shared 22ch cap. A long value ends in an ellipsis and is shown in full in the row's dialog.

Its columns include `Model`, `OpenSpec` (Yes/No) and `Worktree` (`--` when none), and all of them are sortable.

## Session detail

A row opens `SessionDialog`, a native `<dialog>`. It opens with `showModal()`, so Esc, focus-trapping and an inert background come for free. CSS turns it into a full-screen sheet under 640px. It stays mounted across selections, so a poll updates it in place without losing scroll position.

The dialog shows these, top to bottom:

- The session ID under the title. The list's Session ID column is wide-layout only.
- The recap block.
- The `Detail` section.
- `DeleteControls`, described under [Delete](#delete).

`Detail` holds these:

- The current-context figure.
- `TokensChart`, described under [Chart](#chart).
- The pinned `ContextBreakdownPanel`.
- The "All responses" table.
- The "what filled the context" tables, by tool and largest increases.

## Delete

`DeleteControls` confirm or cancel, then call `useDeleteSession`. They are disabled with a note when the session is live. A 409 during the confirm step surfaces the server's message. They are hidden entirely when `useMeta().is_local` is false.

## Chart

### Loading and drawing

`TokensChart` lazily `import()`s `vega-embed`. That way the Sessions page, the first thing a phone opens, does not pay for the bundle until a detail view needs it. The chart rebuilds and re-embeds its spec whenever the turns or the theme change.

The spec draws stacked Cache read, Cache written and New bars. It marks cache misses with ▼ and draws compaction as dashed rules.

### Hover and click

This applies when the chart has a `breakdown`. Hovering a bar shows a compact category tooltip. The tooltip is a vega-tooltip `formatTooltip` that escapes every transcript-derived string. A click or tap reports the response number.

An invisible hit-zone layer under the bars gives every response a full-height strip one step wide, so hover and click work even when hundreds of bars are a pixel wide. The selected bar stays solid and the others dim. A Vega signal drives that, so selecting never re-embeds.

The tooltip element is moved into the enclosing `<dialog>`, because a modal sits in the browser's top layer above anything left in `<body>`.

### The breakdown panel

`Detail` then pins `ContextBreakdownPanel` under the chart. It lists every category with its tokens and its share of that response's own context, never of a model window. Startup categories are marked `~` as estimates.

Categories expand to items. The panel is collapsed by default and dismissable, and it is replaced when another bar is picked. `web/src/lib/contextBreakdown.ts` holds the share, row and tooltip logic.
