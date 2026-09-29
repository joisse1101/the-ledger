# Frontend: shell and theme

> Requirements live in `openspec/specs/responsive-layout/spec.md`. This page describes how the code meets them, not what it must do.

- **Shell** (`web/src/components/AppShell.tsx`, `Nav.tsx`, `RefreshControl.tsx`, `ServerBanner.tsx`,
  `ThemeToggle.tsx`): `AppShell` picks a `useViewportClass()` (`narrow`/`medium`/`wide`, matchMedia
  at 640/1024px, `web/src/hooks/useViewportClass.ts`; the boundaries live only in `web/src/lib/breakpoints.ts`, and the
  stylesheets write `@media (--narrow)`/`(--medium-up)`/`(--wide-up)`, which `web/build/mediaAliases.ts`, a
  PostCSS plugin wired in `vite.config.ts`, swaps for the real queries at build time) and renders `Nav` as a top bar (medium/wide) or a fixed
  bottom tab bar (narrow, `viewport !== "narrow"` puts it in the header instead). `ServerBanner`
  shows a dismissible-by-retry notice above the page when a query is failing but keeps the page's
  last data visible underneath; `unauthorized` instead swaps the whole `<Outlet/>` for `SignInNeeded`
  (pointing back at the printed URL/QR).
- **Theme** (`web/src/theme/theme.ts`): `data-theme` on `<html>`, seeded from `localStorage` (guarded
  try/catch — private windows etc.) else `prefers-color-scheme`, applied *before* React even mounts.
  A module-level store (not per-component `useState`) notifies every subscriber — the toggle button
  and every chart that needs to recolor on theme change — via `useSyncExternalStore`, the same
  pattern `useViewportClass` uses; a live media-query listener keeps it in sync with the OS if
  nothing's been explicitly chosen yet. `web/src/theme/tokens.css` holds the light/dark CSS variables:
  the palette (backgrounds, text, brand, borders, feedback, syntax, shadows, inputs) and font families
  are a manual copy of `@joisse1101/ui-library`'s theme variables under that library's own names
  (`--bg-main`, `--text-main`, `--brand-accent`, `--brand-text`, `--syntax-keyword`, …; provenance and
  version are in the file's header comment), so components copied from the library work unchanged.
  The package is **not** a dependency — refresh by re-copying the variable blocks from
  the package's `dist/ui-library.css` (not in this repo). <!-- docs-check: ignore -->
  App-only tokens with no library equivalent stay alongside: the 8-slot
  categorical palette (`--cat-0`..`--cat-7`, fixed slot order so a chart's `chartColors()`/
  `themeColors()` (see [Frontend overview](Frontend-Overview.md)) never has to duplicate a hex value), `--muted-ink`, and
  `--warn-bg`/`--warn-text`. Fonts (Figtree/Urbanist/JetBrains Mono) load from Google Fonts via
  `index.html`, falling back to system fonts offline; the heading/link/code rules in `app.css`
  mirror the library's `_core_theme.scss`.

Dark/light theme is chosen per device, not shared server-side: each browser picks up
`prefers-color-scheme` until it toggles the switch itself, then remembers that choice in its own
`localStorage` (see `web/src/theme/theme.ts`).
