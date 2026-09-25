import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import { RemoteModeControl } from "./RemoteModeControl";

function stubApi(isLocal: boolean, remote: { enabled: boolean; expires_at: string | null }) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const body = url.startsWith("/api/remote-mode")
      ? JSON.parse(String(init?.body)).enabled
        ? { enabled: true, expires_at: new Date(Date.now() + 8 * 3_600_000).toISOString() }
        : { enabled: false, expires_at: null }
      : { refreshed_at: null, is_local: isLocal, remote_mode: remote };
    return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderControl() {
  const client = createQueryClient();
  render(
    <QueryClientProvider client={client}>
      <RemoteModeControl />
    </QueryClientProvider>,
  );
  return client;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RemoteModeControl", () => {
  it("is a switch on the machine running the app, and turning it on posts enabled: true", async () => {
    const fetchMock = stubApi(true, { enabled: false, expires_at: null });
    const client = renderControl();

    const toggle = await screen.findByRole("switch", { name: /Remote mode/ });
    expect(toggle).not.toBeChecked();
    fireEvent.click(toggle);

    await waitFor(() => expect(screen.getByRole("switch", { name: /Remote mode/ })).toBeChecked());
    const post = fetchMock.mock.calls.find(([url]) => url === "/api/remote-mode");
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ enabled: true });
    // The time left lives in the switch's tooltip.
    expect(screen.getByRole("tooltip")).toHaveTextContent(/8h 0m left/);
    client.clear();
  });

  it("is read-only text on another device, with the time left when on", async () => {
    stubApi(false, { enabled: true, expires_at: new Date(Date.now() + 3 * 3_600_000 + 30_000).toISOString() });
    const client = renderControl();

    expect(await screen.findByText(/Remote mode: on, 3h 0m left/)).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    client.clear();
  });

  it("says off on another device when it is off", async () => {
    stubApi(false, { enabled: false, expires_at: null });
    const client = renderControl();

    expect(await screen.findByText("Remote mode: off")).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    client.clear();
  });
});
