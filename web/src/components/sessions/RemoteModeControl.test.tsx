import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { RemoteMode } from "../../api/types";
import { RemoteModeControl } from "./RemoteModeControl";

type Remote = Partial<RemoteMode> & { enabled: boolean; expires_at: string | null };

const SIGN_IN_QR = {
  svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect width="1" height="1"/></svg>',
  display_url: "https://192.168.1.20:8080",
  expires_at: null,
};

function remoteMode(remote: Remote): RemoteMode {
  return { state: remote.enabled ? "ready" : "off", step: null, reason: null, ...remote };
}

function stubApi(isLocal: boolean, remote: Remote) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    let body: unknown;
    if (url === "/api/remote-mode/qr") {
      body = SIGN_IN_QR;
    } else if (url.startsWith("/api/remote-mode")) {
      body = JSON.parse(String(init?.body)).enabled
        ? remoteMode({ enabled: true, expires_at: new Date(Date.now() + 8 * 3_600_000).toISOString() })
        : remoteMode({ enabled: false, expires_at: null });
    } else {
      body = { refreshed_at: null, is_local: isLocal, remote_mode: remoteMode(remote) };
    }
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

  it("shows that it is starting, not on, and disables the code button", async () => {
    stubApi(true, { enabled: false, expires_at: null, state: "starting", step: "gateway" });
    const client = renderControl();

    expect(await screen.findByText("Starting the gateway…")).toBeInTheDocument();
    // Checked so it can be switched off to cancel, but nothing says it is on and there is no time left.
    expect(screen.getByRole("switch", { name: /Remote mode/ })).toBeChecked();
    expect(screen.getByRole("tooltip")).not.toHaveTextContent(/left/);
    expect(screen.getByRole("button", { name: "QR code" })).toBeDisabled();
    client.clear();
  });

  it("switching it off while starting posts enabled: false", async () => {
    const fetchMock = stubApi(true, { enabled: false, expires_at: null, state: "starting", step: "docker" });
    const client = renderControl();

    fireEvent.click(await screen.findByRole("switch", { name: /Remote mode/ }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url === "/api/remote-mode")).toBe(true));
    const post = fetchMock.mock.calls.find(([url]) => url === "/api/remote-mode");
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ enabled: false });
    client.clear();
  });

  it("shows why it could not start, with the switch off", async () => {
    stubApi(true, { enabled: false, expires_at: null, state: "failed", reason: "Docker Desktop is not installed" });
    const client = renderControl();

    expect(await screen.findByRole("alert")).toHaveTextContent("Docker Desktop is not installed");
    expect(screen.getByRole("switch", { name: /Remote mode/ })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "QR code" })).toBeDisabled();
    client.clear();
  });

  it("opens the sign-in code in a modal, with the address and no token", async () => {
    const fetchMock = stubApi(true, { enabled: true, expires_at: new Date(Date.now() + 3 * 3_600_000).toISOString() });
    const client = renderControl();

    const button = await screen.findByRole("button", { name: "QR code" });
    expect(button).toBeEnabled();
    expect(fetchMock.mock.calls.some(([url]) => url === "/api/remote-mode/qr")).toBe(false);
    fireEvent.click(button);

    const dialog = await screen.findByRole("dialog", { name: "Open on another device" });
    const image = await within(dialog).findByRole("img", { name: "Sign-in QR code" });
    expect(image.getAttribute("src")).toMatch(/^data:image\/svg\+xml/);
    expect(within(dialog).getByText("https://192.168.1.20:8080")).toBeInTheDocument();
    expect(dialog.textContent).not.toMatch(/token/i);

    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("img", { name: "Sign-in QR code" })).not.toBeInTheDocument());
    client.clear();
  });

  it("shows no code button on another device, even while it is starting", async () => {
    stubApi(false, { enabled: false, expires_at: null, state: "starting", step: "docker" });
    const client = renderControl();

    expect(await screen.findByText("Remote mode: starting")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "QR code" })).not.toBeInTheDocument();
    client.clear();
  });
});
