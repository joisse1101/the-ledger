# Guide: Overview

See how much you use Claude Code across all your projects: counts, time, cost, tokens and the hours you work.
A token is the unit Claude counts text in. Context is how many tokens one request sent.

## Read the Overview

1. Open **Overview** in the top bar.
2. Pick a time range from the row of buttons: All time, Today, Yesterday, Past week, Past month, Past quarter or Past year.
3. Read the donut chart at the top left. It shows each project's share of your sessions, and a legend names the projects.
4. Read the grid of figures beside it. See the list below.
5. Scroll to **Messages & Cost by Project**. Each bar is a percentage of the top project, so Messages and Cost can share one axis.
6. Scroll to **Activity by Hour of Day**. Sessions use the left axis and Messages use the right. The two axes have different scales, so compare the shapes of the lines.
7. Hover a chart to see exact values in a tooltip.

## The figures in the grid

- Counts: Projects, Sessions, Messages, and Avg. messages / session.
- Time: Avg. session, Total duration, Longest session and Shortest session.
- Cost: Avg. session cost, Total cost, Most expensive session and Cheapest session.
- Tokens: Avg. tokens / session, Total tokens, Most tokens and Least tokens.

Hover a longest, shortest, most expensive, cheapest, most or least figure to see the project and session it belongs to. A figure marked with an asterisk is an estimate. Hover it for what the estimate leaves out.

## When nothing shows

- With All time selected the page says "No Claude session transcripts found."
- With another range it says no sessions were found for that range. Try a wider range.

## Refresh the data

1. Use the refresh button at the right of the top bar. Its label is "Refresh data".
2. It rescans Claude Code's files and shows the time of the last refresh.

## Checked and unchecked

- Checked: every name above against `OverviewPage.tsx` and the components it shows (the range buttons, the grid labels and the chart headings).
- Unchecked: the chart shapes and tooltips were read from the source only, not seen in a running browser.
- Checked: the refresh control is in the top bar (`AppShell.tsx`, `RefreshControl.tsx`).

## More detail

- [Frontend: Overview](Frontend-Overview.md) explains how the page and charts are built.
- `openspec/specs/web-dashboard/spec.md` holds the requirements.
