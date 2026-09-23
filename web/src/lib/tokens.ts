// Token-count humanising, mirroring claude_context.py's humanise_tokens/format_growth so both
// languages agree on what a Context figure reads as. The server already sends a ready-made `label`
// for the Live list; this is for values the API sends as raw numbers (the All list's Context column,
// the detail view's "Current context" figure).

/** 742 -> "742", 80,618 -> "81k", 1,234,567 -> "1.2M". Keep in step with claude_context.humanise_tokens. */
export function humanizeTokens(n: number): string {
  if (n < 1000) return String(Math.round(n));
  const thousands = Math.round(n / 1000);
  if (thousands < 1000) return `${thousands}k`;
  return `${(n / 1_000_000).toFixed(1)}M`;
}

/** Same scale, but keeps one decimal in the k range so a small delta doesn't round to "0k". */
function humanizeDelta(n: number): string {
  if (n < 1000) return String(Math.round(n));
  const k = n / 1000;
  if (Math.round(k * 10) / 10 < 1000) return `${k.toFixed(1)}k`;
  return `${(n / 1_000_000).toFixed(1)}M`;
}

/** "▲ +2.1k" / "▼ -500" / "• 0", matching claude_context.format_growth. */
export function formatGrowth(delta: number): string {
  if (delta === 0) return "• 0";
  const marker = delta > 0 ? "▲" : "▼";
  const sign = delta > 0 ? "+" : "-";
  return `${marker} ${sign}${humanizeDelta(Math.abs(delta))}`;
}
