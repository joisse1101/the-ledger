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

function renderList(expandedPaths: string[] = []) {
  const client = createQueryClient();
  const onToggle = vi.fn();
  render(
    <QueryClientProvider client={client}>
      <ProjectsList
        expandedPaths={new Set(expandedPaths)}
        onToggle={onToggle}
        renderExpanded={(p) => <div>Details for {p.name}</div>}
      />
    </QueryClientProvider>,
  );
  return { client, onToggle };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe.each([
  ["on the machine running the app", true],
  ["on another device", false],
])("ProjectsList toggling %s", (_where, isLocal) => {
  it("toggles the clicked project and starts no delete", async () => {
    stubApi(isLocal);
    const { client, onToggle } = renderList();
    const button = await screen.findByRole("button", { name: "Show details for demo" });

    fireEvent.click(button);

    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(onToggle).toHaveBeenCalledWith(expect.objectContaining({ path: project.path }));
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(vi.mocked(fetch).mock.calls.every(([, init]) => (init as RequestInit | undefined)?.method !== "DELETE")).toBe(
      true,
    );
    client.clear();
  });
});

describe("ProjectsList", () => {
  it("accents and shows details for an expanded project's row", async () => {
    stubApi(true);
    const { client } = renderList([project.path]);

    await waitFor(() => expect(document.querySelector("tr.row-selected")).not.toBeNull());
    expect(await screen.findByText("Details for demo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide details for demo" })).toBeInTheDocument();
    client.clear();
  });

  it("accents nothing and shows no details while no project is expanded", async () => {
    stubApi(true);
    const { client } = renderList([]);
    await screen.findByRole("button", { name: "Show details for demo" });

    expect(document.querySelector(".row-selected")).toBeNull();
    expect(screen.queryByText("Details for demo")).not.toBeInTheDocument();
    client.clear();
  });
});
