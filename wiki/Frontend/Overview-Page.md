# Frontend: overview page

This page explains how the Overview page and its charts are built. Read it before changing them. The same chart components also serve the Projects panel (see [Frontend projects](Projects-Page.md)).

> Requirements live in `openspec/specs/web-dashboard/spec.md`. This page describes how the code meets them, not what it must do.

## Where the code is

- `web/src/components/overview/` holds the Overview components.
- `web/src/pages/OverviewPage.tsx` is the page.

## Time range

`TimeRangeSelector` is a `ButtonSelector` (single-select, hidden label) over the same seven ranges as `overview_stats.TIME_RANGES`.

## Shared chart colors and group props

`chartTheme.ts` centralizes how charts get their colors. Its `chartColors()`, `groupColorScale()` and `groupColorMap()` read the CSS-variable palette and turn the API's `group_order` into a Vega-Lite domain and range, with `"Other"` always the muted ink. `GroupDonutChart` and `GroupBarChart` share this.

Both charts take `groups`, `groupOrder` and a `groupLabel`. The label is `"project"` on Overview and `"worktree"` in the Projects panel, worded "branch / worktree". It drives their headings, aria labels, tooltip titles and captions.

## The charts

### `GroupDonutChart`

It draws its own color key as a plain HTML list (`GroupLegend`) instead of a Vega-Lite legend, so long group names wrap instead of clipping.

### `GroupBarChart`

Its heading is "Messages & Cost by Project", or "…by Branch / Worktree" in the Projects panel. It normalizes each measure to a percent of its own peak. This is a non-dual-axis choice, so two differently scaled measures can share one axis.

### `ActivityLineChart`

Its heading is "Activity by Hour of Day". It is a layered dual-axis line chart of absolute counts, in 30-minute blocks with smoothed lines. Sessions sit on the left axis and Messages on the right (`resolve.scale.y: "independent"`), with gridlines on the left only.

It adds a grey "Activity trend" layer from `web/src/lib/activityTrend.ts`. The layer takes each measure as a share of its own peak, averages them, then applies a 3-block moving average. It sits on its own hidden 0-100 scale, and a caption note explains the calculation.

### Shared behavior

`GroupBarChart` and `ActivityLineChart` both keep "Messages" on the same categorical hue (`hues[0]`). All three charts use the shared `useVegaEmbed` hook (`useVegaEmbed.ts`), which lazily imports `vega-embed` and re-embeds when the spec changes. It is the general form of the pattern `TokensChart` uses directly.

## Summary tiles

`SummaryStats` renders the KPI tiles. The four extreme figures are buttons that toggle an inline disclosure naming their project or session, plus a `title` attribute for hover on pointer devices. Buttons are used because a touchscreen has no hover-only affordance.
