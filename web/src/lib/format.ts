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
 *  exact, Claude-Code-reported figure or a best-effort estimate - see `ESTIMATED_COST_TOOLTIP`
 *  and `CostFigure`, which mark the latter. */
export function formatCost(value: number | null | undefined): string {
  return value == null ? "--" : `$${value.toFixed(2)}`;
}

function joinWithAnd(items: string[]): string {
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** Explains why a cost is a best-effort estimate rather than Claude Code's own reported figure,
 *  shown in `CostFigure`'s tooltip. Names the specific model(s) this app's pricing table didn't
 *  recognize when the per-message fallback scan found any (`unpricedModels`); otherwise falls back
 *  to a generic message - this covers Claude Code's own `cost-state` flagging the session as
 *  unpriced without this app's local scan finding a specific model (e.g. subagent spend on a model
 *  never mentioned in the session's own transcript lines), and a session still in progress. */
export function estimatedCostTooltip(unpricedModels: string[]): string {
  if (unpricedModels.length === 0) {
    return (
      "Best-effort estimate: it excludes any subagent spend, and Claude Code flagged part of this " +
      "session's cost as unpriced in a way this app can't attribute to a specific model."
    );
  }
  const models = joinWithAnd(unpricedModels);
  const plural = unpricedModels.length > 1;
  return (
    `Best-effort estimate: it excludes any subagent spend, and this app doesn't yet recognize ` +
    `${plural ? "these models" : "this model"} (${models}), so ${plural ? "their" : "its"} turns aren't priced.`
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
