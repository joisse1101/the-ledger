## Context

`web/src/theme/tokens.css` defines the app's colours as CSS variables (`--bg`, `--surface`, `--text`,
`--text-2`, `--grid`, `--accent`, `--danger`, `--warn-*`, `--cat-0..7`, `--muted-ink`) plus layout
tokens. About 90 `var(--…)` references across `styles/{app,overview,sessions}.css` use them, and two
places read them at runtime via `getComputedStyle` to colour Vega charts (`overview/chartTheme.ts`,
`sessions/TokensChart.tsx`). `theme/theme.ts` owns the light/dark choice (per device, `localStorage`,
follows `prefers-color-scheme`) and sets `data-theme` on `<html>`; `index.html` applies a saved
choice before first paint.

`@joisse1101/ui-library` publishes a compiled `ui-library.css` whose theme blocks are
`:root,[data-theme=dark]{…}` and `[data-theme=light]{…}`, using its own variable names. Locally it is
present only as a yalc link (`web/.yalc`, gitignored). See proposal.md for why it is copied rather
than depended on.

## Goals / Non-Goals

**Goals:**
- The app's colours come from the library's palette, under the library's variable names, so components
  copied in later work without re-mapping.
- A fresh clone builds and looks identical to this machine: nothing depends on yalc or a registry.

**Non-Goals:**
- Adopting `ThemeProvider` or any library component (a later change, if at all).
- Changing `theme.ts` behaviour, the categorical chart palette, spacing/layout tokens, or typography.
- Tracking future library palette changes automatically.

## Decisions

**Copy compiled CSS values, not `_variables.scss`.** The `_variables.scss` file is the library's
source of truth but needs `sass` (a new devDependency) and a build step to become variables. The
theme blocks in `dist/ui-library.css` are already plain custom-property declarations, so they paste
straight into `tokens.css`. Alternative considered: depend on `sass` and `@use` the SCSS — rejected as
tooling for a one-off copy.

**Adopt the library's variable names everywhere (rename, don't alias).** An alias layer
(`--bg: var(--bg-main)`) would be a smaller diff but leaves two vocabularies; the point is that copied
components read the library's names. The rename is mechanical (fixed 7-name mapping, see proposal),
and verified by grepping for the old names.

**Copy the whole theme variable set, not just what the app uses today.** Includes shadows, input,
border and `-rgb` variants. Costs ~70 declarations per theme but means a component copied later
doesn't hit an undefined variable. The library's component-level variables (`--btn-*` etc., in its
non-theme `:root` block) are *not* copied; they come with the components.

**Keep the app's own theme structure, fill it with the library's values.** Light values as the
`:root` default, dark under `:root[data-theme="dark"]`, and the `prefers-color-scheme: dark`
fallback under `:root:not([data-theme])`. The library defaults to dark on bare `:root`, which would
flash dark on a light-preferring device before `theme.ts` runs. `color-scheme` stays set directly per
theme as today; the library's `--color-scheme` variable isn't needed.

**Library values for the shared roles; app values for the rest.** `--warn-bg`/`--warn-text` stay the
app's own (per-theme) because the library's warning chip is one fixed light colour in both themes and
would glare on dark. `--on-accent` (white on the accent) and `--cat-0..7`/`--muted-ink` (a validated
8-slot categorical palette with no library equivalent) stay as they are.

**Don't import the library's global CSS.** Its stylesheet also carries `html`/`h1`–`h6`/`a` rules and
a Google Fonts `@import`. Copying only the variable blocks avoids restyling headings and links and
keeps the app free of external network requests.

**No `ThemeProvider`.** Controlled by our store it would only re-set the same `data-theme`
attribute `theme.ts` already sets. Revisit if a copied component calls the library's `useTheme`.

**Remove yalc last.** The copy reads from `web/.yalc`, so deleting the link is the final group of
tasks. Reverting c385a82 first was considered and rejected: it wouldn't remove the untracked
`web/.yalc`, `yalc.lock` or the `node_modules` link, and it would delete the source needed for the copy.
The link itself is removed rather than `npm uninstall`ed, since the package was never in
`dependencies`.

## Risks / Trade-offs

- [A missed rename leaves a variable undefined; CSS silently drops the declaration and a chart gets an
  empty colour string] → the old definitions are deleted from `tokens.css` and a grep for the old
  names must come back empty; charts are checked visually in both themes.
- [The palette shifts the look (dusty-rose accent, pinker backgrounds) and contrast changes] → visual
  pass over Sessions (list + dialog), Overview, Projects and the notices in both themes and at a
  narrow width; white-on-accent for buttons/switches checked by eye.
- [The copied values drift from the library over time] → a comment at the top of `tokens.css` records
  the source and the library version they were taken from; refreshing is a manual re-copy.
- [Copied theme variables the app doesn't use yet are dead weight] → accepted, ~140 lines, for the
  drop-in-components benefit.


## Revisions during apply

- The first copy came from the stale yalc snapshot (`web/.yalc`), which lacked `--brand-text` and
  `--syntax-*` and had older feedback/accent values. The palette is now copied from the library
  repo's current `dist/ui-library.css` (v2.0.0). Syntax tokens are kept for rendering session text.
- The library's `--text-on-accent` replaces the app-only `--on-accent`.
- Fonts are now adopted (Figtree body, Urbanist headings, JetBrains Mono code) via a Google Fonts
  `<link>` in `index.html`, reversing the earlier "stay offline-clean" decision at the user's request;
  system fonts remain the fallback. Text rules for body/headings/links/code (font, colour, heading
  tracking and weights) mirror `_core_theme.scss`; sizes, spacing, `p` colour, cards and scrollbars do not.
