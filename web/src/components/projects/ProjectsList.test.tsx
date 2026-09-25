import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import { ProjectsList } from "./ProjectsList";

const project = {
  path: "C:\repos\demo",
  name: "demo",
  trust_accepted: true,
  last_session_id: null,
  last_version: "2.0.0",
  last_cost: null,
  last_start_time: null,
  last_duration_ms: null,
  lines_added: null,
  lines_removed: null,
  mcp_servers: [],
};

/** jsdom has no matchMedia; every query "matches", so the list renders as the wide table. */
function stubWideViewport() {
  vi.stubGlobal(
    "matchMedia",
    (query: string) => ({
      matches: true,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }),
  );
}

function stubApi(isLocal: boolean) {
  stubWideViewport();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const body = url.startsWith("/api/meta")
        ? { refreshed_at: null, is_local: isLocal }
        : { projects: [project] };
      return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
    }),
  );
}

function renderList() {
  const client = createQueryClient();
  render(
    <QueryClientProvider client={client}>
      <ProjectsList />
    </QueryClientProvider>,
  );
  return client;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProjectsList delete flow", () => {
  it("offers the delete confirmation on the machine running the app", async () => {
    stubApi(true);
    const client = renderList();
    const row = (await screen.findAllByText("demo"))[0];

    // Clicking is idempotent, so retry until /api/meta has answered and the click is honored.
    await waitFor(() => {
      fireEvent.click(row);
      expect(screen.getByRole("button", { name: "Confirm delete" })).toBeInTheDocument();
    });
    client.clear();
  });

  it("names the row button for what selecting it does", async () => {
    stubApi(true);
    const client = renderList();
    await screen.findAllByText("demo");

    // The label depends on /api/meta having answered, so wait for it.
    const button = await screen.findByRole("button", { name: "Select project demo to delete" });
    fireEvent.click(button);
    expect(await screen.findByRole("button", { name: "Confirm delete" })).toBeInTheDocument();
    client.clear();
  });

  it("never offers it from another device", async () => {
    stubApi(false);
    const client = renderList();
    const row = (await screen.findAllByText("demo"))[0];
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/meta", expect.anything()));
    await new Promise((resolve) => setTimeout(resolve, 20));

    fireEvent.click(row);
    expect(screen.queryByRole("button", { name: "Confirm delete" })).not.toBeInTheDocument();
    client.clear();
  });
});
