import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { RemoteQr, RemoteQrAddress } from "../../api/types";
import { RemoteQrDialog } from "./RemoteQrDialog";

const TAILSCALE: RemoteQrAddress = {
  kind: "tailscale",
  address: "https://100.64.0.7:8080",
  display_url: "https://100.64.0.7:8080",
  svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect id="tailscale" width="1" height="1"/></svg>',
};
const LAN: RemoteQrAddress = {
  kind: "lan",
  address: "https://192.168.1.20:8080",
  display_url: "https://192.168.1.20:8080",
  svg: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect id="lan" width="1" height="1"/></svg>',
};

function stubQr(addresses: RemoteQrAddress[]) {
  const [first] = addresses;
  const qr: RemoteQr = { svg: first.svg, display_url: first.display_url, expires_at: null, addresses };
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(qr), { status: 200, headers: { "content-type": "application/json" } })),
  );
}

function renderDialog() {
  const client = createQueryClient();
  render(
    <QueryClientProvider client={client}>
      <RemoteQrDialog open onClose={() => {}} />
    </QueryClientProvider>,
  );
  return client;
}

function decodedSrc(image: HTMLElement) {
  return decodeURIComponent(String(image.getAttribute("src")));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RemoteQrDialog", () => {
  it("selects Tailscale first and shows its code and address", async () => {
    stubQr([TAILSCALE, LAN]);
    const client = renderDialog();

    const image = await screen.findByRole("img", { name: "Sign-in QR code" });
    expect(screen.getByRole("radio", { name: "Tailscale" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "LAN" })).not.toBeChecked();
    expect(decodedSrc(image)).toContain('id="tailscale"');
    expect(screen.getByText(TAILSCALE.display_url)).toBeInTheDocument();
    client.clear();
  });

  it("changes the image and the address when switching to LAN", async () => {
    stubQr([TAILSCALE, LAN]);
    const client = renderDialog();

    await screen.findByRole("img", { name: "Sign-in QR code" });
    fireEvent.click(screen.getByRole("radio", { name: "LAN" }));

    const image = screen.getByRole("img", { name: "Sign-in QR code" });
    expect(screen.getByRole("radio", { name: "LAN" })).toBeChecked();
    expect(decodedSrc(image)).toContain('id="lan"');
    expect(decodedSrc(image)).not.toContain('id="tailscale"');
    expect(screen.getByText(LAN.display_url)).toBeInTheDocument();
    expect(screen.queryByText(TAILSCALE.display_url)).not.toBeInTheDocument();
    client.clear();
  });

  it("shows no address control when there is one kind of address", async () => {
    stubQr([LAN]);
    const client = renderDialog();

    const image = await screen.findByRole("img", { name: "Sign-in QR code" });
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
    expect(decodedSrc(image)).toContain('id="lan"');
    expect(screen.getByText(LAN.display_url)).toBeInTheDocument();
    client.clear();
  });

  it("puts no token text in the dialog", async () => {
    stubQr([TAILSCALE, LAN]);
    const client = renderDialog();

    const dialog = await screen.findByRole("dialog", { name: "Open on another device" });
    await within(dialog).findByRole("img", { name: "Sign-in QR code" });
    expect(dialog.textContent).not.toMatch(/token/i);
    client.clear();
  });
});
