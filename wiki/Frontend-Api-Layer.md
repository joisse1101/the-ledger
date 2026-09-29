# Frontend: API layer

Vite + React + TypeScript + React Router + TanStack Query; plain hand-written CSS (no component
library, no Sass): global stylesheets in `styles/` (`app.css`, `overview.css`, `sessions.css`) plus
`web/src/theme/tokens.css`, and newer components as colocated CSS modules (`Switch.tsx` +
`Switch.module.css`: one flat camelCase class per element, sizes/variants as component-scoped custom
properties, colours only from the `tokens.css` variables, `className` on the root element and every
other prop on the underlying control). Migrate a component to a module when touching it; don't
rewrite `styles/` wholesale. Inline SVG icons in `web/src/components/icons.tsx`. Both `npm run dev` and `npm run preview` proxy `/api` to
`http://127.0.0.1:8501` (`vite.config.ts`'s `server.proxy`/`preview.proxy`, kept in sync), so the
page is always same-origin with the API whether run directly or through the gateway — the frontend
never needs a different-origin API client. `web/src/main.tsx` wires up
`QueryClientProvider`/`BrowserRouter`; `App.tsx` is the route table (`/` → Sessions, `/overview`,
`/projects`, everything else redirects to `/`, since `vite preview`'s SPA fallback serves `index.html` for
any unknown path) rendered inside `AppShell`.

- **API layer** (`web/src/api/`): `token.ts` is the frontend's whole sign-in story —
  `consumeTokenFromUrl()` runs in `main.tsx` before React renders, stores a printed link's
  `?token=` in `localStorage` (try/catch-guarded) and strips it from the address bar via
  `history.replaceState`; `getStoredToken()` reads it back. `client.ts`'s `apiFetch` is the one
  place that calls `fetch` — it sends that token as `Authorization: Bearer <token>` when one is
  stored, adds `X-Requested-With: ledger` on non-GET requests (matching `security.py`'s CSRF check),
  and turns every failure into one of `ApiError` (the server answered with a non-2xx; carries
  FastAPI's `detail` message), `UnauthorizedError` (401 — this device isn't signed in), or
  `NetworkError` (fetch itself failed/threw). `queries.ts` has one TanStack Query hook per endpoint
  (`useMeta`, `useRefresh`, `useLive`, `useTranscripts` — an `useInfiniteQuery` for "Load more"
  paging, `useSession`, `useOverview`, `useProjects`, `useDeleteSession`, `useDeleteProject`,
  `usePendingDecision`, `useAnswerDecision`, `useSetRemoteMode`, `useOpenRepo`);
  `useLive({auto})` sets `refetchInterval` to `2000` or `false` and disables background polling so a
  hidden tab stops hitting the server. `queryClient.ts` retries a dropped connection once
  (`NetworkError`) but never retries a real API error. `serverStatus.ts`'s `useServerProblem()` scans
  the query cache for failing *observed* queries (ones a mounted component is still watching) to
  decide what banner, if any, `AppShell` should show (`unauthorized` beats `error` beats
  `unreachable`), and clears itself once a retried query succeeds. `types.ts` mirrors the server's
  JSON shapes 1:1 (dates as ISO strings; the client formats/`--`s them).
