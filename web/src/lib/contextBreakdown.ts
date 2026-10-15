// Turns the server's per-response breakdown into the rows both the hover tooltip and the pinned
// panel show. Percentages are a row's share of that response's OWN context, never of a model's
// window (the transcript doesn't record the window size).

import type { BreakdownItem, ContextBreakdown } from "../api/types";
import { formatCount } from "./format";

export const REMAINDER_NAME = "Everything else";
export const REMAINDER_NOTE = "System prompt, built-in tools and any compaction summary";
const TOOLTIP_ROWS = 5;

export interface BreakdownRow {
  name: string;
  tokens: number;
  /** Startup categories are estimates; growth rows and the remainder are exact. */
  estimated: boolean;
  items: BreakdownItem[];
  note?: string;
}

/** `tokens` as a whole-number percentage of `context`: 6,700 of 28,300 is "24%". */
export function formatShare(tokens: number, context: number): string {
  if (context <= 0) return "0%";
  const percent = Math.round((tokens / context) * 100);
  return percent === 0 && tokens > 0 ? "<1%" : `${percent}%`;
}

/** Every row of one response's breakdown, largest first. They sum to the response's context. */
export function responseRows(breakdown: ContextBreakdown, index: number): BreakdownRow[] {
  const turn = breakdown.turns[index];
  const snapshot = turn && breakdown.snapshots[turn.snapshot];
  if (!turn || !snapshot) return [];

  const rows: BreakdownRow[] = [
    ...snapshot.categories.map((c) => ({ name: c.name, tokens: c.tokens, estimated: true, items: c.items })),
    ...turn.growth.map((g) => ({ name: g.tool, tokens: g.tokens, estimated: false, items: [] })),
    { name: REMAINDER_NAME, tokens: turn.remainder, estimated: false, items: [], note: REMAINDER_NOTE },
  ];
  return rows.sort((a, b) => b.tokens - a.tokens);
}

export interface TooltipContent {
  title: string;
  lines: { name: string; value: string }[];
  /** Set when any listed figure is an estimate. */
  estimateNote: string | null;
}

/** The compact hover view: the context size and the largest categories only, never items. */
export function tooltipContent(rows: BreakdownRow[], response: number, context: number): TooltipContent {
  const top = rows.filter((r) => r.tokens > 0).slice(0, TOOLTIP_ROWS);
  return {
    title: `Response ${response}: ${formatCount(context)} tokens`,
    lines: top.map((r) => ({
      name: r.name,
      value: `${r.estimated ? "~" : ""}${formatCount(r.tokens)} (${formatShare(r.tokens, context)})`,
    })),
    estimateNote: top.some((r) => r.estimated) ? "~ estimated from the transcript" : null,
  };
}
