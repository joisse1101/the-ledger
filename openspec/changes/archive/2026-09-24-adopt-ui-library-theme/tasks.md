## 1. Copy the palette

- [x] 1.1 Extract the `:root,[data-theme=dark]{…}` and `[data-theme=light]{…}` theme blocks from `web/.yalc/@joisse1101/ui-library/dist/ui-library.css` (theme variables only — not the component `--btn-*` block, not the global element rules or `@import`s); note the library version from its `package.json`
- [x] 1.2 Rewrite `web/src/theme/tokens.css`: light values as `:root`, dark values under `:root[data-theme="dark"]` and the `prefers-color-scheme: dark` `:root:not([data-theme])` fallback, `color-scheme` set per theme as before
- [x] 1.3 Keep the app-only tokens in each theme block: `--cat-0..7`, `--muted-ink`, `--on-accent`, `--warn-bg`/`--warn-text`, and the layout tokens (`--tap`, `--gutter`, `--radius`, `--tabbar-h`, `--header-h`)
- [x] 1.4 Add a header comment to `tokens.css` recording the source (`@joisse1101/ui-library`, version) and that values are a manual copy

## 2. Rename to the library's variable names

- [x] 2.1 In `styles/app.css`, `styles/overview.css`, `styles/sessions.css`: `--bg`→`--bg-main`, `--surface`→`--bg-surface`, `--text`→`--text-main`, `--text-2`→`--text-muted`, `--grid`→`--border-subtle`, `--accent`→`--brand-accent`, `--danger`→`--color-danger` (match whole names only: `--text` must not hit `--text-2`, `--bg` must not hit `--bg-main`)
- [x] 2.2 Update the variable names read by `components/overview/chartTheme.ts` (`chartColors`) and `components/sessions/TokensChart.tsx` (`themeColors`), and their comments
- [x] 2.3 Grep `web/src` (CSS, TS, TSX, tests) and `web/index.html` for each old name; result must be empty

## 3. Verify

- [x] 3.1 `cd web && npm run build` and `npm test` pass
- [x] 3.2 Check in a browser, light and dark: Sessions (Live + All lists, session dialog with `TokensChart`, delete confirm), Overview (all three charts, summary tiles), Projects, the server banner / sign-in notice, `--warn-*` notices
- [x] 3.3 Check a narrow viewport (bottom tab bar) and the theme toggle
- [x] 3.4 With no saved choice and the OS set to dark, reload: first paint is dark, no light flash

## 4. Remove the yalc link

- [x] 4.1 `web/package.json`: delete the `dev:link`, `dev:update` and `build:unlink` scripts (leave `dev:force` only if wanted independently — it is not yalc-specific)
- [x] 4.2 `.gitignore`: delete the `.yalc` and `yalc.lock` lines added in c385a82
- [x] 4.3 Delete `web/.yalc/`, `web/yalc.lock`, and the `web/node_modules/@joisse1101` link (remove the link itself, not the directory it points at)
- [x] 4.4 From a clean state (`rm -r web/node_modules && npm ci`), `npm run build` succeeds and `git status` shows only intended changes

## 5. Docs

- [x] 5.1 Update `CLAUDE.md`'s Theme section (`tokens.css` now carries the library's palette under its variable names, plus the app-only `--cat-*`/`--muted-ink`/`--warn-*`/`--on-accent`), and mention the copy/provenance and that the package is not a dependency
