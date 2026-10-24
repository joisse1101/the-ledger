import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../api/queryClient";
import { Nav } from "./Nav";

function stubMeta(enabled: boolean, isLocal = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            refreshed_at: null,
            is_local: isLocal,
            remote_mode: { enabled, expires_at: null, state: enabled ? "ready" : "off", step: null, reason: null },
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
    ),
  );
}

function renderNav() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter>
        <Nav viewport="wide" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("Nav", () => {
  it("hides the Files page while Remote mode is off", async () => {
    stubMeta(false);
    renderNav();

    await screen.findByRole("link", { name: "Overview" });
    expect(screen.queryByRole("link", { name: "Files" })).not.toBeInTheDocument();
  });

  it("shows the Files page while Remote mode is on", async () => {
    stubMeta(true);
    renderNav();

    expect(await screen.findByRole("link", { name: "Files" })).toHaveAttribute("href", "/files");
  });

  it("shows Settings to a browser on the machine running the app, with or without Remote mode", async () => {
    for (const remote of [false, true]) {
      stubMeta(remote, true);
      const { unmount } = renderNav();

      expect(await screen.findByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
      unmount();
    }
  });

  it("hides Settings from any other device, with or without Remote mode", async () => {
    for (const remote of [false, true]) {
      stubMeta(remote, false);
      const { unmount } = renderNav();

      await screen.findByRole("link", { name: "Overview" });
      expect(screen.queryByRole("link", { name: "Settings" })).not.toBeInTheDocument();
      unmount();
    }
  });
});
