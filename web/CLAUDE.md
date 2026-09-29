# web/ — React + Vite frontend

| Working on | Read |
|---|---|
| `src/api/` (token, client, queries) | [Frontend-Api-Layer](../wiki/Frontend-Api-Layer.md) |
| Shell, nav, theme, `tokens.css` | [Frontend-Shell-And-Theme](../wiki/Frontend-Shell-And-Theme.md) |
| Live and All session pages | [Frontend-Sessions](../wiki/Frontend-Sessions.md) |
| Overview page and charts | [Frontend-Overview](../wiki/Frontend-Overview.md) |
| Projects page | [Frontend-Projects](../wiki/Frontend-Projects.md) |
| `ButtonSelector`, `ConfirmDialog`, `lib/` | [Frontend-Shared-Components](../wiki/Frontend-Shared-Components.md) |
| Test list | [Testing](../wiki/Testing.md) |

## Local rules

- `npm run build` type-checks (`tsc --noEmit`); run it before calling a change done.
- New components use a colocated CSS module. Colours come only from the `tokens.css` variables.
  Migrate an old component when touching it; don't rewrite `src/styles/` wholesale.
- Breakpoints live only in `web/src/lib/breakpoints.ts`; stylesheets use `@media (--narrow)` and friends.
- `web/src/api/types.ts` mirrors the server JSON. Change both sides together.
- Call the API only through `apiFetch`, with relative `/api` paths.
- No E2E harness: verify responsive layout by resizing a real browser.
