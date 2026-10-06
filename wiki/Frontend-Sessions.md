# Frontend: sessions

> Requirements live in `openspec/specs/web-dashboard/spec.md`, `openspec/specs/remote-session-control/spec.md`. This page describes how the code meets them, not what it must do.

- **Sessions** (`components/sessions/`, `web/src/pages/LiveSessionsPage.tsx` at `/`, `web/src/pages/SessionsPage.tsx` at
  `/sessions`): Live and All are separate pages. Each keeps its selection in the URL (`?session=<id>`),
  so a reload/shared link reopens it. **Live** (`LiveSessionsPage`): `LiveList` polls via `useLive`, with
  its own "Auto-refresh" switch and frozen "Last refreshed" caption when off; selecting a row renders
  `LiveSessionPanel` *under the list* (not a dialog) with `LiveControl` — a control-only view: the
  session's oldest pending prompt rendered by `DecisionPrompt` (Approve/Deny with an optional reason
  for a permission prompt; the real options, multi-select and free text for an `AskUserQuestion`, via
  `web/src/lib/prompt.ts`) and an "Open repo window" button (`useOpenRepo`). The panel reads the Live list from
  the query cache with `auto: false`, so only `LiveList`'s switch drives polling.
  `usePendingDecision` polls while it's mounted; a prompt that vanishes without this view having
  answered it says the session already moved on (as does a 409) instead of going blank, and it shows
  nothing on a non-local device while Remote mode is off. `LiveList` badges a row (`pending-badge`)
  from `/api/live`'s `pending_decision`, and carries `RemoteModeControl`: a switch on the machine
  running the app (`is_local`), read-only "Remote mode: on, 7h left" text elsewhere. **All**
  (`SessionsPage`): `AllList` debounces its search box (`useDebouncedValue`, 300ms), drives
  `Project`/`Version`/`Branch` `FilterMultiselect`s (`<details>`-based checkbox lists — no
  popover/portal machinery needed) off the API's option lists, and pages 50-at-a-time via
  `useTranscripts`'s "Load more". Its columns include `Model` and `OpenSpec` (Yes/No), both sortable. A row opens `SessionDialog`, a native `<dialog>` (`showModal()`, so
  Esc/focus-trapping/inert background come for free; CSS turns it into a full-screen sheet under
  640px) kept mounted across selections so a poll updates it in place without losing scroll position.
  It shows the recap block, its `Detail` section (current-context figure, `TokensChart`, "All
  responses" table, "what filled the context" by-tool/largest-increases tables) and `DeleteControls`
  (confirm/cancel → `useDeleteSession`, disabled with a note when live, a 409 mid-confirm surfaces the
  server's message; hidden entirely when `useMeta().is_local` is false). `TokensChart` lazily
  `import()`s `vega-embed` (so the Sessions page, the first thing a phone opens, doesn't pay for its
  bundle cost until a detail view needs it) and rebuilds/re-embeds its spec whenever the turns or the
  theme change; its spec draws the stacked Cache read/Cache written/New bars with ▼ cache-miss markers
  and dashed compaction rules.
