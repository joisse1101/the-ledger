import { QueryClientProvider, QueryObserver } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "./queryClient";
import { apiFetch } from "./client";
import {
  keys,
  LIVE_POLL_MS,
  useAnswerDecision,
  useOpenRepo,
  usePendingDecision,
  useSetRemoteMode,
} from "./queries";
import type { DecisionAnswer, LiveResponse } from "./types";

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

describe("the session control hooks", () => {
  function wrapper(client: ReturnType<typeof createQueryClient>) {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  }

  it("polls a session's pending decision at its own endpoint, and not without an id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ pending_decision: null }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createQueryClient();

    const idle = renderHook(() => usePendingDecision(null), { wrapper: wrapper(client) });
    expect(idle.result.current.fetchStatus).toBe("idle");
    expect(fetchMock).not.toHaveBeenCalled();

    const { result } = renderHook(() => usePendingDecision("abc-123"), { wrapper: wrapper(client) });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock.mock.calls[0][0]).toBe("/api/sessions/abc-123/pending-decision");
    client.clear();
  });

  it("answers a prompt at its own id, with a JSON body and the CSRF header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ answered: "p1" }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createQueryClient();

    const { result } = renderHook(() => useAnswerDecision("abc"), { wrapper: wrapper(client) });
    await act(() =>
      result.current.mutateAsync({ promptId: "p1", answer: { decision: "deny", reason: "not that file" } }),
    );

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/sessions/abc/decisions/p1/answer");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ decision: "deny", reason: "not that file" });
    expect(init.headers.get("X-Requested-With")).toBe("ledger");
    expect(init.headers.get("Content-Type")).toBe("application/json");
    client.clear();
  });

  const shapes: [string, DecisionAnswer][] = [
    ["approve", { decision: "allow" }],
    [
      "answer a question",
      { decision: "answer", answers: { "Which extras?": ["auth", "logs"], "Which db?": "sqlite" } },
    ],
  ];
  it.each(shapes)("sends the %s shape as is", async (_name, answer) => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ answered: "p2" }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createQueryClient();

    const { result } = renderHook(() => useAnswerDecision("abc"), { wrapper: wrapper(client) });
    await act(() => result.current.mutateAsync({ promptId: "p2", answer }));

    expect(fetchMock.mock.calls[0][0]).toBe("/api/sessions/abc/decisions/p2/answer");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(answer);
    client.clear();
  });

  it("surfaces a 409 from answering as an ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "no pending decision for this session" }), {
          status: 409,
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    const client = createQueryClient();

    const { result } = renderHook(() => useAnswerDecision("abc"), { wrapper: wrapper(client) });
    await expect(
      act(() => result.current.mutateAsync({ promptId: "p1", answer: { decision: "allow" } })),
    ).rejects.toMatchObject({ status: 409 });
    client.clear();
  });

  it("sets Remote mode with a JSON body and puts the reply into the cached meta", async () => {
    const remoteMode = { enabled: true, expires_at: "2026-09-24T20:00:00+00:00" };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(remoteMode));
    vi.stubGlobal("fetch", fetchMock);
    const client = createQueryClient();
    client.setQueryData(keys.meta, {
      refreshed_at: null,
      is_local: true,
      remote_mode: { enabled: false, expires_at: null },
    });

    const { result } = renderHook(() => useSetRemoteMode(), { wrapper: wrapper(client) });
    await act(() => result.current.mutateAsync(true));

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/remote-mode");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ enabled: true });
    expect(init.headers.get("X-Requested-With")).toBe("ledger");
    expect(client.getQueryData<{ remote_mode: unknown }>(keys.meta)?.remote_mode).toEqual(remoteMode);
    client.clear();
  });

  it("surfaces a 403 when another device tries to set Remote mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "switching Remote mode requires a local request" }), {
          status: 403,
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    const client = createQueryClient();

    const { result } = renderHook(() => useSetRemoteMode(), { wrapper: wrapper(client) });
    await expect(act(() => result.current.mutateAsync(true))).rejects.toMatchObject({ status: 403 });
    client.clear();
  });

  it("opens a repo with a bodiless, CSRF-headed POST", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ opened: "abc" }));
    vi.stubGlobal("fetch", fetchMock);
    const client = createQueryClient();

    const { result } = renderHook(() => useOpenRepo("abc"), { wrapper: wrapper(client) });
    await act(() => result.current.mutateAsync());

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/sessions/abc/open-repo");
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
    expect(init.headers.get("X-Requested-With")).toBe("ledger");
    client.clear();
  });
});
