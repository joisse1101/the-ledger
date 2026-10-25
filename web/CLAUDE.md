# web/ — React + Vite frontend

| Working on | Read |
|---|---|
| `src/api/` (token, client, queries) | [Frontend-Api-Layer](../wiki/Frontend-Api-Layer.md) |
| Shell, nav, theme, `tokens.css` | [Frontend-Shell-And-Theme](../wiki/Frontend-Shell-And-Theme.md) |
| Live and All session pages | [Frontend-Sessions](../wiki/Frontend-Sessions.md) |
| Overview page and charts | [Frontend-Overview](../wiki/Frontend-Overview.md) |
| Projects page | [Frontend-Projects](../wiki/Frontend-Projects.md) |
| Files page, `upload.ts` | [Frontend-Files](../wiki/Frontend-Files.md) |
| `ButtonSelector`, `ConfirmDialog`, `lib/` | [Frontend-Shared-Components](../wiki/Frontend-Shared-Components.md) |
| Test list | [Testing](../wiki/Testing.md) |

## Local rules

- `npm run build` type-checks (`tsc --noEmit`); run it before calling a change done.
- General standards: the toolkit rules in [the-toolbox](https://github.com/joisse1101/the-toolbox) (its installer takes `-Scope project`).
- Colours come from `tokens.css` variables. Migrate an old component when touching it; don't
  rewrite `src/styles/` wholesale.
- Breakpoints live in `web/src/lib/breakpoints.ts`; stylesheets use `@media (--narrow)` and friends.
- `web/src/api/types.ts` mirrors the server JSON.
- The API client is `apiFetch`, with relative `/api` paths.
- No E2E harness: verify responsive layout by resizing a real browser.
