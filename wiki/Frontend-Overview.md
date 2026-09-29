# Frontend: overview

> Requirements live in `openspec/specs/web-dashboard/spec.md`. This page describes how the code meets them, not what it must do.

- **Overview** (`components/overview/`, `web/src/pages/OverviewPage.tsx`): `TimeRangeSelector` is a
  `ButtonSelector` (single-select, hidden label) over the same seven ranges as `overview_stats.TIME_RANGES`.
  `chartTheme.ts`'s `chartColors()`/`groupColorScale()`/`groupColorMap()` centralize reading the
  CSS-variable palette and turning the API's `group_order` into a Vega-Lite domain/range (`"Other"`
  always the muted ink) shared by `GroupDonutChart` and `GroupBarChart`; both take `groups`,
  `groupOrder` and a `groupLabel` (`"project"` on Overview, `"branch"` in the Projects panel) that
  drives their headings, aria labels, tooltip titles and captions. `GroupDonutChart` draws
  its own color key as a plain HTML list (`GroupLegend`) instead of a Vega-Lite legend so long
  group names wrap instead of clipping. `GroupBarChart` ("Messages & Cost by Project"/"…by Branch")
  normalizes each measure to % of its own peak (a non-dual-axis choice so two differently-scaled
  measures can share one axis). `ActivityLineChart` ("Activity by Hour of Day", in 30-minute blocks, smoothed lines, plus a grey "Activity trend" layer from `web/src/lib/activityTrend.ts`: each measure as a share of its own peak, averaged, then a 3-block moving average, on its own hidden 0-100 scale, with the calculation explained in a caption note) instead is a layered
  dual-axis line chart of absolute counts — Sessions on the left axis, Messages on the right
  (`resolve.scale.y: "independent"`), gridlines on the left only. Both keep "Messages" on the same
  categorical hue (`hues[0]`). All three charts use the shared `useVegaEmbed` hook
  (lazy `vega-embed` import, re-embeds on spec change, `useVegaEmbed.ts` — the general form of the
  pattern `TokensChart` uses directly). `SummaryStats` renders the KPI tiles; the four extreme
  figures are buttons that toggle an inline disclosure naming their project/session (plus a `title`
  attribute for hover on pointer devices) since there's no hover-only affordance on a touchscreen.
