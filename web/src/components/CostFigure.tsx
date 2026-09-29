import type { CostSource } from "../api/types";
import { estimatedCostTooltip } from "../lib/format";
import { Tooltip } from "./Tooltip";

export interface CostFigureProps {
  /** Already formatted, e.g. via `formatCost` or a server-sent `MoneyFigure.label`. */
  label: string;
  source: CostSource | null | undefined;
  /** Model ids this app's pricing table didn't recognize, if any - named in the tooltip. */
  unpricedModels?: string[];
  /** True only when Claude Code's own `cost-state` line flagged this session as unpriced. */
  costStateFlagged?: boolean;
}

/** A cost figure as shown anywhere in the app: plain when it's Claude Code's own exact, reported
 *  cost, or marked with an asterisk and an explanatory tooltip when it's this app's best-effort
 *  estimate. */
export function CostFigure({ label, source, unpricedModels = [], costStateFlagged = false }: CostFigureProps) {
  if (source !== "estimated") return <>{label}</>;
  return (
    <span className="cost-figure">
      {label}*
      <Tooltip tooltip={estimatedCostTooltip(unpricedModels, costStateFlagged)} size="sm" />
    </span>
  );
}
