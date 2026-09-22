import { QueryObserver } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "./queryClient";
import { apiFetch } from "./client";
import { keys, LIVE_POLL_MS } from "./queries";
import type { LiveResponse } from "./types";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

// Exercises the same QueryObserver configuration useLive() builds, without going
// through React rendering - what's under test is the query client's behavior
// (keeping stale data visible through a failed background refetch), not React's
// commit timing.
function liveObserver(client: ReturnType<typeof createQueryClient>) {
  return new QueryObserver<LiveResponse>(client, {
    queryKey: keys.live,
    queryFn: () => apiFetch<LiveResponse>("/api/live"),
    refetchInterval: LIVE_POLL_MS,
  });
}

describe("the Live query", () => {
  it("keeps the previous data when a refetch's network call fails", async () => {
    const sessions = [{ session_id: "abc" }];
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ sessions }))
      // The query client retries a dropped connection once (see queryClient.ts).
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const client = createQueryClient();
    const observer = liveObserver(client);

    // A QueryObserver only fetches once it has a subscriber.
    const unsubscribe = observer.subscribe(() => {});
    await vi.waitFor(() => expect(observer.getCurrentResult().isSuccess).toBe(true));
    expect(observer.getCurrentResult().data?.sessions).toEqual(sessions);

    await observer.refetch();

    expect(observer.getCurrentResult().isError).toBe(true);
    // The failed refetch didn't blank the list: the last good rows are still there.
    expect(observer.getCurrentResult().data?.sessions).toEqual(sessions);

    unsubscribe();
    client.clear();
  });
});
