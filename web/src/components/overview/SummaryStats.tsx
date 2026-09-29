import type { OverviewSummary } from "../../api/types";
import { formatContext, formatCount } from "../../lib/format";
import { CostFigure } from "../CostFigure";
import { StatGrid, type StatTile } from "../StatGrid";

function tiles(summary: OverviewSummary): StatTile[] {
  return [
    { label: "Projects", value: formatCount(summary.projects) },
    { label: "Sessions", value: formatCount(summary.sessions) },
    { label: "Messages", value: formatCount(summary.messages) },
    {
      label: "Avg. messages / session",
      value: summary.avg_messages_per_session != null ? summary.avg_messages_per_session.toFixed(1) : "--",
    },

    { label: "Avg. session", value: summary.duration.average.label },
    { label: "Total duration", value: summary.duration.total.label },
    { label: "Longest session", value: summary.duration.longest.label, ref: summary.duration.longest },
    { label: "Shortest session", value: summary.duration.shortest.label, ref: summary.duration.shortest },

    { label: "Avg. session cost", value: summary.cost.average.label },
    { label: "Total cost", value: summary.cost.total.label },
    {
      label: "Most expensive session",
      value: (
        <CostFigure
          label={summary.cost.most_expensive.label}
          source={summary.cost.most_expensive.cost_source}
          unpricedModels={summary.cost.most_expensive.unpriced_models}
        />
      ),
      ref: summary.cost.most_expensive,
    },
    {
      label: "Cheapest session",
      value: (
        <CostFigure
          label={summary.cost.cheapest.label}
          source={summary.cost.cheapest.cost_source}
          unpricedModels={summary.cost.cheapest.unpriced_models}
        />
      ),
      ref: summary.cost.cheapest,
    },

    { label: "Avg. tokens / session", value: formatContext(summary.tokens.average) },
    { label: "Total tokens", value: formatContext(summary.tokens.total) },
    { label: "Most tokens", value: formatContext(summary.tokens.most.amount), ref: summary.tokens.most },
    { label: "Least tokens", value: formatContext(summary.tokens.least.amount), ref: summary.tokens.least },
  ];
}

export interface SummaryStatsProps {
  summary: OverviewSummary;
}

/** The Overview KPI grid: counts, session-duration, session-cost, and context-token figures for the
 *  selected time range. The six extreme figures (longest/shortest/most-expensive/cheapest/most-tokens/
 *  least-tokens) carry a tooltip naming the project and session they belong to. */
export function SummaryStats({ summary }: SummaryStatsProps) {
  return <StatGrid tiles={tiles(summary)} />;
}
