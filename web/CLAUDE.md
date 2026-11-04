# web/ — React + Vite frontend

| Working on | Read |
|---|---|
| `web/src/api/` (token, client, queries) | [Frontend: API layer](../wiki/Frontend/Api-Layer.md) |
| Shell, nav, theme, `tokens.css` | [Frontend: shell and theme](../wiki/Frontend/Shell-And-Theme.md) |
| Live and All session pages | [Frontend: sessions page](../wiki/Frontend/Sessions-Page.md) |
| Overview page and charts | [Frontend: overview page](../wiki/Frontend/Overview-Page.md) |
| Projects page | [Frontend: projects page](../wiki/Frontend/Projects-Page.md) |
| Files page, `upload.ts` | [Frontend: files page](../wiki/Frontend/Files-Page.md) |
| `ButtonSelector`, `ConfirmDialog`, `lib/` | [Frontend: shared components](../wiki/Frontend/Shared-Components.md) |
| Test list | [Testing](../wiki/Contributing/Testing.md) |

## Local rules

- `npm run build` type-checks (`tsc --noEmit`); run it before calling a change done.
- Colours come from `tokens.css` variables. Migrate an old component when touching it; don't
  rewrite `web/src/styles/` wholesale.
- Breakpoints live in `web/src/lib/breakpoints.ts`; stylesheets use `@media (--narrow)` and friends.
- `web/src/api/types.ts` mirrors the server JSON.
- The API client is `apiFetch`, with relative `/api` paths.
- No E2E harness: verify responsive layout by resizing a real browser.
