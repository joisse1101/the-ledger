## Why

The dashboard's look should come from `@joisse1101/ui-library`'s palette so it matches the rest of that
design system, and so components can later be copied over without re-mapping variable names. The
package can't be a real dependency: it is only reachable through a local `yalc` link (gitignored), so
a fresh clone can't resolve it, and this app is local-only and shared by cloning the repo, not
deployed. So the palette is copied in, and the yalc link is dropped.

## What Changes

- Copy the library's theme variables (light + dark: backgrounds, text, brand, borders, feedback
  colours, shadows, inputs) into `web/src/theme/tokens.css` as plain CSS, keeping the library's
  variable names.
- Rename the app's own tokens to the library's names across `styles/*.css` and the chart code that
  reads colours via `getComputedStyle` (`--bg` → `--bg-main`, `--surface` → `--bg-surface`,
  `--text` → `--text-main`, `--text-2` → `--text-muted`, `--grid` → `--border-subtle`,
  `--accent` → `--brand-accent`, `--danger` → `--color-danger`).
- Keep the app-only tokens that have no library equivalent: `--cat-0..7`, `--muted-ink`,
  `--on-accent`, `--warn-bg`/`--warn-text` (the library's warning chip is fixed-light, wrong on dark),
  and the layout tokens (`--tap`, `--gutter`, `--radius`, `--tabbar-h`, `--header-h`).
- Keep today's theme mechanics: light is the default, dark under `data-theme="dark"`, and a
  `prefers-color-scheme` fallback before JS runs (the library's own structure defaults to dark and
  would flash dark on light-preferring devices). `theme/theme.ts` stays the source of truth
  (per-device choice, remembered in `localStorage`).
- Do not copy the library's global element rules (`html`, `h1`–`h6`, `a`) or its Google Fonts
  `@import`: the app stays offline-clean and its typography unchanged.
- **Remove the yalc link**: drop the `dev:link`, `dev:update` and `build:unlink` scripts and the
  `.yalc`/`yalc.lock` gitignore lines added in c385a82, and delete `web/.yalc`, `web/yalc.lock` and
  the `node_modules/@joisse1101` symlink. Done last, since the copy reads from `web/.yalc`.
- The library's `ThemeProvider` is not adopted: in controlled mode it only sets `data-theme`, which
  `theme.ts` already does. Revisit when components are copied over, if any of them call its
  `useTheme`.

Visible result: the app moves to the library's dusty-rose accent and slightly pinker backgrounds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The `web-dashboard` "Theme is chosen per device" requirement (light/dark, device default,
per-device toggle, charts follow the theme) and "a project keeps its colour in every chart" are
unchanged; the specs don't name colours. This change is tooling/styling only, so
`.openspec.yaml` sets `skip_specs: true`.

## Impact

- `web/src/theme/tokens.css` (rewritten), `web/src/styles/{app,overview,sessions}.css` (variable
  rename), `web/src/components/overview/chartTheme.ts` and `web/src/components/sessions/TokensChart.tsx`
  (variable names read by the charts).
- `web/package.json`, `.gitignore`, and removal of untracked yalc files; no new dependencies.
- `CLAUDE.md`'s theme notes (`tokens.css`, `--cat-*`, `--muted-ink`) need updating.
- No API, gateway or hooks changes.
