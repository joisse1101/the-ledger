# Frontend: shell and theme

This page explains how the app shell (navigation, layout classes, server banner), the Settings page and the light/dark theme are built. Read it before changing them.

> Requirements live in `openspec/specs/responsive-layout/spec.md`. This page describes how the code meets them, not what it must do.

## Shell

Files: `web/src/components/AppShell.tsx`, `Nav.tsx`, `RefreshControl.tsx`, `ServerBanner.tsx`, `ThemeToggle.tsx`.

### Viewport classes

`AppShell` picks a `useViewportClass()` of `narrow`, `medium` or `wide`. It uses matchMedia at 640 and 1024px (`web/src/hooks/useViewportClass.ts`). The boundaries live only in `web/src/lib/breakpoints.ts`.

The stylesheets write `@media (--narrow)`, `(--medium-up)` and `(--wide-up)`. `web/build/mediaAliases.ts`, a PostCSS plugin wired in `vite.config.ts`, swaps those for the real queries at build time.

### Page width

The page area (`main.content`) is capped at 100rem and centred on every page. The header's inner row (`.topbar-inner`) uses the same cap and the same side padding, `--page-gutter-x` in `tokens.css` (the normal `--gutter` on narrow, 1.5rem on medium, 2rem on wide), so brand, page title, tables and the right-hand controls share one left and one right edge on every page. The first and last cells of a table drop their own side padding so table text sits on that edge too.

Small text has a floor: `--font-xs` is 12px and `--font-sm` about 13px, raised in rem on wide screens to cancel the 80% desktop root. Chart labels use `MIN_CHART_TEXT_PX` (12) from `lib/uiScale.ts`. `--danger-text` is the red used on its own tint (the Needs compact chip) and meets 4.5:1 in both themes. Text and number inputs share the `.field` class in `app.css`.

### Navigation

`AppShell` renders `Nav` as a top bar at medium and wide, or as a fixed bottom tab bar at narrow. At narrow, `viewport !== "narrow"` puts the nav in the header instead. Below wide, links use their short labels (`labelMobile`) and the refresh caption drops its label. The top links are plain tabs with no fill: the active one has a 2px accent underline and the hovered one a faint underline; the bottom bar is one row for any number of tabs.

### Server banner

`ServerBanner` shows a dismissible-by-retry notice above the page when a query is failing, and keeps the page's last data visible underneath. When the problem is `unauthorized`, `AppShell` instead swaps the whole `<Outlet/>` for `SignInNeeded`, which points back at the printed URL or QR.

## Settings

Files: `web/src/pages/SettingsPage.tsx`, route `/settings`.

### Visibility

`Nav` entries can be `remoteOnly` (Files) or `localOnly`. Settings is `localOnly`, so it shows only while `useMeta().data.is_local` is true, meaning a browser on the machine running the app, with or without Remote mode. The page renders `<Navigate to="/">` for any other device, without asking for the settings. The server refuses the routes regardless, so hiding is only UX.

### Worktree folders

The page's main part is the worktree-folder list. The built-in `.claude/worktrees` is listed with a "Built in" label and no Remove button. User folders each have Remove, and an input adds one. <!-- docs-check: ignore -->

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

`tokens.css` holds the light and dark CSS variables. The palette (backgrounds, text, brand, borders, feedback, syntax, shadows, inputs) and the font families are a manual copy of `@joisse1101/ui-library`'s theme variables under that library's own names, such as `--bg-main`, `--text-main`, `--brand-accent`, `--brand-text` and `--syntax-keyword`. Provenance and version are in the file's header comment. Components copied from the library therefore work unchanged. <!-- docs-check: ignore -->

The package is **not** a dependency. Refresh by re-copying the variable blocks from the package's `dist/ui-library.css` (not in this repo). <!-- docs-check: ignore -->

App-only tokens with no library equivalent stay alongside:

- The 8-slot categorical palette (`--cat-0`..`--cat-7`). Its slot order is fixed so a chart's `chartColors()` or `themeColors()` (see [Frontend overview](Overview-Page.md)) never has to duplicate a hex value.
- `--muted-ink`.
- `--warn-bg` and `--warn-text`.

### Fonts

Fonts (Figtree, Urbanist, JetBrains Mono) load from Google Fonts via `index.html`, falling back to system fonts offline. The heading, link and code rules in `app.css` mirror the library's `_core_theme.scss`.

Form fields (`.field`, filter buttons, sort select) use the darker `--input-border` token, not `--border-subtle`, so their edges reach 3:1 contrast.
