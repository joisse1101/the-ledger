# Frontend: shell and theme

This page explains how the app shell (navigation, layout classes, server banner), the Settings page and the light/dark theme are built. Read it before changing them.

> Requirements live in `openspec/specs/responsive-layout/spec.md`. This page describes how the code meets them, not what it must do.

## Shell

Files: `web/src/components/AppShell.tsx`, `Nav.tsx`, `RefreshControl.tsx`, `ServerBanner.tsx`, `ThemeToggle.tsx`.

### Viewport classes

`AppShell` picks a `useViewportClass()` of `narrow`, `medium` or `wide`. It uses matchMedia at 640 and 1024px (`web/src/hooks/useViewportClass.ts`). The boundaries live only in `web/src/lib/breakpoints.ts`.

The stylesheets write `@media (--narrow)`, `(--medium-up)` and `(--wide-up)`. `web/build/mediaAliases.ts`, a PostCSS plugin wired in `vite.config.ts`, swaps those for the real queries at build time.

### Navigation

`AppShell` renders `Nav` as a top bar at medium and wide, or as a fixed bottom tab bar at narrow. At narrow, `viewport !== "narrow"` puts the nav in the header instead.

### Server banner

`ServerBanner` shows a dismissible-by-retry notice above the page when a query is failing, and keeps the page's last data visible underneath. When the problem is `unauthorized`, `AppShell` instead swaps the whole `<Outlet/>` for `SignInNeeded`, which points back at the printed URL or QR.

## Settings

Files: `web/src/pages/SettingsPage.tsx`, route `/settings`.

### Visibility

`Nav` entries can be `remoteOnly` (Files) or `localOnly`. Settings is `localOnly`, so it shows only while `useMeta().data.is_local` is true, meaning a browser on the machine running the app, with or without Remote mode. The page renders `<Navigate to="/">` for any other device, without asking for the settings. The server refuses the routes regardless, so hiding is only UX.

### Worktree folders

The page's main part is the worktree-folder list. The built-in `.claude/worktrees` is listed with a "Built in" label and no Remove button. User folders each have Remove, and an input adds one.

Every add or remove sends the whole user list to `PUT /api/settings` (`useSaveSettings`) at once. The controls are disabled and "Saving..." shows while the server re-files sessions. If a folder is refused, its reason shows inline and the input and list stay as they were. On success the transcripts, session, overview, projects and live queries reload.

### Desktop widget section

Below the folders, a "Desktop widget" section holds the widget's settings. Each Save sends only its own field, and the server saves it without re-filing sessions, so nothing else is reloaded. Each form is `noValidate`, so a rejected number shows the server's reason inline (same as a refused folder) and the typed value stays.

The fields are:

- A number input (1 to 10, 5 until set) for how many projects the widget's Ledger-button tooltip lists. Save sends `{widget: {max_projects}}` (`useSaveWidgetMaxProjects`).
- "AFK minutes (1 to 240)", 30 until set, for how long the widget's AFK switch stays on. Save sends `{widget: {afk_minutes}}` (`useSaveWidgetAfkMinutes`).
- "Break minutes (1 to 240)", 60 until set, in the "Break workouts" block: the minutes of work before the widget opens its break window. Save sends `{widget: {break_minutes}}` (`useSaveWidgetBreakMinutes`).

The projects field follows the saved number until the user types, and saving folders leaves it alone. A new AFK number applies the next time the switch is turned on. A line above the break input says the widget takes a new break length within about 30 seconds.

Below the break input, the "Break workouts" block shows the personal workouts folder's path, which is the ignored `mine` folder under the widget's `workouts` folder, created on first open. An Open folder button (`useOpenWorkoutsFolder`, `POST /api/widget/workouts/open`) opens it. If opening fails, the server's message, which names the folder, shows inline.

## Theme

### Choosing and applying

The theme code is `web/src/theme/theme.ts`. It sets `data-theme` on `<html>`, seeded from `localStorage` (guarded try/catch, for private windows etc.) and otherwise from `prefers-color-scheme`. It is applied before React even mounts.

A module-level store, not per-component `useState`, notifies every subscriber via `useSyncExternalStore`. The subscribers are the toggle button and every chart that needs to recolor on theme change. `useViewportClass` uses the same pattern. A live media-query listener keeps the store in sync with the OS if nothing has been explicitly chosen yet.

The theme is chosen per device, not shared server-side. Each browser picks up `prefers-color-scheme` until it toggles the switch itself, then remembers that choice in its own `localStorage`.

### Tokens (`web/src/theme/tokens.css`)

`tokens.css` holds the light and dark CSS variables. The palette (backgrounds, text, brand, borders, feedback, syntax, shadows, inputs) and the font families are a manual copy of `@joisse1101/ui-library`'s theme variables under that library's own names, such as `--bg-main`, `--text-main`, `--brand-accent`, `--brand-text` and `--syntax-keyword`. Provenance and version are in the file's header comment. Components copied from the library therefore work unchanged.

The package is **not** a dependency. Refresh by re-copying the variable blocks from the package's `dist/ui-library.css` (not in this repo). <!-- docs-check: ignore -->

App-only tokens with no library equivalent stay alongside:

- The 8-slot categorical palette (`--cat-0`..`--cat-7`). Its slot order is fixed so a chart's `chartColors()` or `themeColors()` (see [Frontend overview](Frontend-Overview.md)) never has to duplicate a hex value.
- `--muted-ink`.
- `--warn-bg` and `--warn-text`.

### Fonts

Fonts (Figtree, Urbanist, JetBrains Mono) load from Google Fonts via `index.html`, falling back to system fonts offline. The heading, link and code rules in `app.css` mirror the library's `_core_theme.scss`.
