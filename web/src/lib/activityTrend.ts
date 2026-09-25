import type { ActivityBucket } from "../api/types";

/** Blocks averaged per trend point (centered): 3 blocks, i.e. 1.5 hours of half-hour blocks or 3 of hourly. */
export const TREND_WINDOW = 3;

/** A combined "how busy is this time of day" curve, 0-100, one value per block.
 *
 *  Sessions and messages are different units on different scales, so each is first expressed
 *  as a share of its own busiest block, then the two shares are averaged (equal weight) and
 *  smoothed with a centered moving average. Blocks near either end average whichever
 *  neighbours exist. */
export function activityTrend(activity: ActivityBucket[], window = TREND_WINDOW): number[] {
  const maxSessions = Math.max(...activity.map((b) => b.sessions), 0) || 1;
  const maxMessages = Math.max(...activity.map((b) => b.messages), 0) || 1;
  const index = activity.map((b) => 50 * (b.sessions / maxSessions + b.messages / maxMessages));

  const reach = Math.floor(window / 2);
  return index.map((_, i) => {
    const slice = index.slice(Math.max(0, i - reach), i + reach + 1);
    return slice.reduce((sum, value) => sum + value, 0) / slice.length;
  });
}
