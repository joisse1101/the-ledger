import { describe, expect, it } from "vitest";
import type { ActivityBucket } from "../api/types";
import { activityTrend } from "./activityTrend";

const block = (minute: number, sessions: number, messages: number): ActivityBucket => ({
  minute,
  label: String(minute),
  sessions,
  messages,
});

describe("activityTrend", () => {
  it("weights sessions and messages equally, each against its own peak", () => {
    // Block 0 is the sessions peak, block 1 the messages peak; window 1 = no smoothing.
    const trend = activityTrend([block(0, 10, 100), block(30, 5, 1000)], 1);
    expect(trend[0]).toBeCloseTo(50 * (1 + 0.1));
    expect(trend[1]).toBeCloseTo(50 * (0.5 + 1));
  });

  it("smooths with a centered moving average, using the neighbours that exist at the ends", () => {
    const trend = activityTrend([block(0, 0, 0), block(30, 6, 6), block(60, 0, 0)], 3);
    expect(trend[0]).toBeCloseTo(50); // (0 + 100) / 2
    expect(trend[1]).toBeCloseTo(100 / 3);
    expect(trend[2]).toBeCloseTo(50);
  });

  it("returns zeros when there is no activity", () => {
    expect(activityTrend([block(0, 0, 0), block(30, 0, 0)])).toEqual([0, 0]);
  });
});
