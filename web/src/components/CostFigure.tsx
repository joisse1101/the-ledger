import type { CostSource } from "../api/types";
import { ESTIMATED_COST_TOOLTIP } from "../lib/format";
import { Tooltip } from "./Tooltip";

export interface CostFigureProps {
  /** Already formatted, e.g. via `formatCost` or a server-sent `MoneyFigure.label`. */
  label: string;
  source: CostSource | null | undefined;
}

/** A cost figure as shown anywhere in the app: plain when it's Claude Code's own exact, reported
 *  cost, or marked with an asterisk and an explanatory tooltip when it's this app's best-effort
 *  estimate. */
export function CostFigure({ label, source }: CostFigureProps) {
  if (source !== "estimated") return <>{label}</>;
  return (
    <span className="cost-figure">
      {label}*
      <Tooltip tooltip={ESTIMATED_COST_TOOLTIP} size="sm" />
    </span>
  );
}
