# Frontend: API layer

This page explains the frontend's stack and how it talks to the API: sign-in token, fetch wrapper, query hooks and error banners. Read it before changing anything under `web/src/api/`.

## Stack and styling

The frontend uses Vite, React, TypeScript, React Router and TanStack Query. Styling is plain hand-written CSS, with no component library and no Sass.

- `styles/` holds the global stylesheets: `app.css`, `overview.css`, `sessions.css`.
- `web/src/theme/tokens.css` holds the theme variables.
- `web/src/components/icons.tsx` holds the inline SVG icons.

Newer components use colocated CSS modules, for example `Switch.tsx` with `Switch.module.css`. A module has one flat camelCase class per element, and sizes and variants are component-scoped custom properties. Colors come only from the `tokens.css` variables. `className` goes on the root element and every other prop on the underlying control.

Migrate a component to a module when touching it. Do not rewrite `styles/` wholesale.

## Proxy and routes

Both `npm run dev` and `npm run preview` proxy `/api` to `http://127.0.0.1:8501` (`vite.config.ts`'s `server.proxy` and `preview.proxy`, kept in sync). The page is therefore always same-origin with the API, whether run directly or through the gateway, and the frontend never needs a different-origin API client.

`web/src/main.tsx` wires up `QueryClientProvider` and `BrowserRouter`. `App.tsx` is the route table, rendered inside `AppShell`. It has `/` for Sessions, `/overview` and `/projects`, and everything else redirects to `/`, since `vite preview`'s SPA fallback serves `index.html` for any unknown path.

## The API layer (`web/src/api/`)

### Sign-in token (`token.ts`)

`token.ts` is the frontend's whole sign-in story. `consumeTokenFromUrl()` runs in `main.tsx` before React renders. It stores a printed link's `?token=` in `localStorage` (try/catch-guarded) and strips it from the address bar via `history.replaceState`. `getStoredToken()` reads it back.

### Fetch wrapper (`client.ts`)

`client.ts`'s `apiFetch` is the one place that calls `fetch`. It sends the stored token, when there is one, as `Authorization: Bearer <token>`. It adds `X-Requested-With: ledger` on non-GET requests, matching `security.py`'s CSRF check.

It turns every failure into one of three errors:

- `ApiError`: the server answered with a non-2xx; it carries FastAPI's `detail` message.
- `UnauthorizedError`: a 401, meaning this device is not signed in.
- `NetworkError`: `fetch` itself failed or threw.

### Query hooks (`queries.ts`)

`queries.ts` has one TanStack Query hook per endpoint:

- `useMeta`
- `useRefresh`
- `useLive`
- `useTranscripts`, an `useInfiniteQuery` for "Load more" paging
- `useSession`
- `useOverview`
- `useProjects`
- `useDeleteSession`
- `useDeleteProject`
- `usePendingDecision`
- `useAnswerDecision`
- `useSetRemoteMode`
- `useOpenRepo`
- `useSettings`
- `useSaveSettings`

`useLive({auto})` sets `refetchInterval` to `2000` or `false`, and disables background polling so a hidden tab stops hitting the server.

`useRefresh` also invalidates `keys.projectRepos` and returns that promise from `onSuccess`. The refresh therefore stays pending until a mounted repos query has refetched, because the server drops its repo cache on `POST /api/refresh` and `gh` is asked again. A failed count read still ends in success, and with no repos query mounted nothing waits on `gh`.

### Retries (`queryClient.ts`)

`queryClient.ts` retries a dropped connection once (`NetworkError`) but never retries a real API error.

### Server problem banner (`serverStatus.ts`)

`serverStatus.ts`'s `useServerProblem()` scans the query cache for failing observed queries, meaning ones a mounted component is still watching. It uses them to decide which banner, if any, `AppShell` should show: `unauthorized` beats `error` beats `unreachable`. It clears itself once a retried query succeeds.

### Types (`types.ts`)

`types.ts` mirrors the server's JSON shapes 1:1. Dates are ISO strings, and the client formats them or shows `--`.
