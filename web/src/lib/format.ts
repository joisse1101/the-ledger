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

/** Dollars with two decimals, or `--` when there is no figure. Costs are estimates. */
export function formatCost(value: number | null | undefined): string {
  return value == null ? "--" : `$${value.toFixed(2)}`;
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
