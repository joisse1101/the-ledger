import { humanizeTokens } from "./tokens";

/** Local time of day as HH:MM:SS (24-hour), or `--` when there is no timestamp. */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
}

/** Local date and time as YYYY-MM-DD HH:MM:SS, or `--` when there is no timestamp. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "--";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "--";
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  );
}

/** Dollars with two decimals, or `--` when there is no figure. A session's cost is either an
 *  exact, Claude-Code-reported figure or a best-effort estimate - see `estimatedCostTooltip`
 *  and `CostFigure`, which mark the latter. */
export function formatCost(value: number | null | undefined): string {
  return value == null ? "--" : `$${value.toFixed(2)}`;
}

function joinWithAnd(items: string[]): string {
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** Explains why a cost is a best-effort estimate rather than Claude Code's own reported figure,
 *  shown in `CostFigure`'s tooltip. States what the shown figure actually covers (a sum of this
 *  session's own priced messages) before naming the gap, so "estimate" doesn't read as an
 *  unqualified disclaimer.
 *
 *  There are three distinct reasons a session ends up here, and the tooltip picks whichever
 *  applies rather than one generic disclaimer (a session can match more than one; the most
 *  specific/actionable reason wins):
 *  1. `unpricedModels` is non-empty: this app's own per-message scan found a model id its pricing
 *     table doesn't recognize - named directly, since that's exactly what to add to fix it.
 *  2. `costStateFlagged`: Claude Code's own `cost-state` line reported `hasUnknownModelCost: true` -
 *     it found a gap (typically subagent spend) this app's own scan can't see at all.
 *  3. Neither: there's no `cost-state` line yet - the session is still in progress, or from a
 *     Claude Code build too old to write one. */
export function estimatedCostTooltip(unpricedModels: string[], costStateFlagged: boolean): string {
  const lead = "Estimate: the sum of this session's own priced messages. It excludes any subagent spend, and ";
  if (unpricedModels.length > 0) {
    const models = joinWithAnd(unpricedModels);
    const plural = unpricedModels.length > 1;
    return (
      lead +
      `this app doesn't yet recognize ${plural ? "these models" : "this model"} (${models}), so ` +
      `${plural ? "their" : "its"} turns aren't priced and the true total is higher than shown.`
    );
  }
  if (costStateFlagged) {
    return (
      lead +
      "Claude Code flagged part of this session's cost as unpriced in a way this app can't attribute " +
      "to a specific model, so the true total is higher than shown."
    );
  }
  return (
    lead +
    "Claude Code hasn't reported a final cost for this session yet - it's either still running, or " +
    "from a build too old to report one - so this total may change."
  );
}

/** A token count, humanised, or `--` when there is none. */
export function formatContext(value: number | null | undefined): string {
  return value == null ? "--" : humanizeTokens(value);
}

/** Any other text field: blank/whitespace-only counts as missing. */
export function formatText(value: string | null | undefined): string {
  return value && value.trim() ? value : "--";
}

/** A plain integer count, or `--` when there is none. */
export function formatCount(value: number | null | undefined): string {
  return value == null ? "--" : value.toLocaleString();
}

/** How long is left, coarsely: `7h 59m`, `45m`, or `<1m`. Nothing left (or a bad figure) is `<1m`. */
export function formatTimeLeft(ms: number): string {
  const minutes = Math.floor(Math.max(0, Number.isFinite(ms) ? ms : 0) / 60_000);
  if (minutes < 1) return "<1m";
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
}
