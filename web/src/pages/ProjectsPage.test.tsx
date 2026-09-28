import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../api/queryClient";
import type { Project } from "../api/types";
import { ProjectsPage } from "./ProjectsPage";

vi.mock("../components/overview/GroupDonutChart", () => ({
  GroupDonutChart: () => <div data-testid="donut" />,
}));
vi.mock("../components/overview/GroupBarChart", () => ({ GroupBarChart: () => null }));
vi.mock("../components/overview/ActivityLineChart", () => ({ ActivityLineChart: () => null }));

const make = (name: string): Project => ({
  path: `C:\\repos\\${name}`,
  name,
  trust_accepted: true,
  last_session_id: null,
  last_version: "2.0.0",
  last_cost: null,
  last_start_time: null,
  last_duration_ms: null,
  lines_added: null,
  lines_removed: null,
  mcp_servers: [],
});
const alpha = make("alpha");
const beta = make("beta");

const populated = {
  range: "All time",
  empty: false,
  summary: {},
  groups: [{ group: "main", sessions: 1, messages: 1, cost: 0, share: 100, messages_pct: 100, cost_pct: 100 }],
  group_order: ["main"],
  activity: [],
};

const json = (body: unknown) =>
  new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });

/** jsdom has no matchMedia; every query "matches", so the list renders as the wide table. */
function stubApi() {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: true,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.startsWith("/api/meta")) return json({ refreshed_at: null, is_local: true });
      if (url.startsWith("/api/overview")) return json(populated);
      if (url.startsWith("/api/projects")) return json({ projects: [alpha, beta] });
      return json({});
    }),
  );
}

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="search">{location.search}</output>;
}

function renderPage(entry = "/projects") {
  const client = createQueryClient();
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[entry]}>
        <ProjectsPage />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}

const search = () => new URLSearchParams(screen.getByTestId("search").textContent ?? "");
const openProjects = () => search().getAll("project");

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProjectsPage", () => {
  it("shows no panel until a project is opened, then shows that project's inline and puts it in the URL", async () => {
    stubApi();
    const client = renderPage();
    const open = await screen.findByRole("button", { name: "Show details for alpha" });
    expect(screen.queryByRole("region", { name: /Charts for/ })).not.toBeInTheDocument();

    fireEvent.click(open);

    expect(await screen.findByRole("region", { name: "Charts for alpha" })).toBeInTheDocument();
    expect(await screen.findByTestId("donut")).toBeInTheDocument();
    expect(openProjects()).toEqual([alpha.path]);
    client.clear();
  });

  it("reopens the project named by ?project= on load", async () => {
    stubApi();
    const client = renderPage(`/projects?project=${encodeURIComponent(beta.path)}`);

    expect(await screen.findByRole("region", { name: "Charts for beta" })).toBeInTheDocument();
    expect(openProjects()).toEqual([beta.path]);
    client.clear();
  });

  it("drops a ?project= that names no known project", async () => {
    stubApi();
    const client = renderPage(`/projects?project=${encodeURIComponent("C:\\repos\\gone")}`);

    await waitFor(() => expect(openProjects()).toEqual([]));
    expect(screen.queryByRole("region", { name: /Charts for/ })).not.toBeInTheDocument();
    client.clear();
  });

  it("drops only the stale entry, keeping any other still-known project open", async () => {
    stubApi();
    const client = renderPage(
      `/projects?project=${encodeURIComponent("C:\\repos\\gone")}&project=${encodeURIComponent(alpha.path)}`,
    );

    await waitFor(() => expect(openProjects()).toEqual([alpha.path]));
    expect(await screen.findByRole("region", { name: "Charts for alpha" })).toBeInTheDocument();
    client.clear();
  });

  it("opens a second project's panel alongside the first, each keeping its own range", async () => {
    stubApi();
    const client = renderPage(`/projects?project=${encodeURIComponent(alpha.path)}`);
    await screen.findByRole("region", { name: "Charts for alpha" });
    fireEvent.click(screen.getByRole("radio", { name: "Past week" }));
    expect(screen.getByRole("radio", { name: "Past week" })).toBeChecked();

    fireEvent.click(screen.getByRole("button", { name: "Show details for beta" }));

    expect(await screen.findByRole("region", { name: "Charts for beta" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Charts for alpha" })).toBeInTheDocument();
    expect(openProjects().sort()).toEqual([alpha.path, beta.path].sort());
    client.clear();
  });

  it("closes a project's panel without touching any other open one", async () => {
    stubApi();
    const client = renderPage(
      `/projects?project=${encodeURIComponent(alpha.path)}&project=${encodeURIComponent(beta.path)}`,
    );
    await screen.findByRole("region", { name: "Charts for alpha" });
    await screen.findByRole("region", { name: "Charts for beta" });

    fireEvent.click(screen.getByRole("button", { name: "Hide details for alpha" }));

    expect(screen.queryByRole("region", { name: "Charts for alpha" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Charts for beta" })).toBeInTheDocument();
    expect(openProjects()).toEqual([beta.path]);
    client.clear();
  });

  it("closes just that project's panel once it is deleted", async () => {
    stubApi();
    const client = renderPage(
      `/projects?project=${encodeURIComponent(alpha.path)}&project=${encodeURIComponent(beta.path)}`,
    );
    const alphaPanel = await screen.findByRole("region", { name: "Charts for alpha" });

    fireEvent.click(await within(alphaPanel).findByRole("button", { name: "Delete project" }));
    fireEvent.click(within(alphaPanel).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(openProjects()).toEqual([beta.path]));
    expect(screen.queryByRole("region", { name: "Charts for alpha" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Charts for beta" })).toBeInTheDocument();
    client.clear();
  });
});
