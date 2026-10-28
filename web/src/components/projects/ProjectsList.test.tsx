import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { Project, ProjectRepo } from "../../api/types";
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

/** jsdom has no matchMedia; every query "matches" (so the list renders as the wide table), or none does (cards). */
function stubViewport(narrow = false) {
  vi.stubGlobal(
    "matchMedia",
    (query: string) => ({
      matches: !narrow,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }),
  );
}

const githubRepo: ProjectRepo = {
  path: project.path,
  host: "GitHub",
  url: "https://github.com/acme/demo",
  issues: 7,
  prs: 2,
};

function stubApi(isLocal: boolean, repos: ProjectRepo[] = [], narrow = false) {
  stubViewport(narrow);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      let body: unknown = { projects: [project] };
      if (url.startsWith("/api/meta")) {
        body = { refreshed_at: null, is_local: isLocal, remote_mode: { enabled: false, expires_at: null, state: "off", step: null, reason: null } };
      } else if (url.startsWith("/api/projects/repos")) {
        body = { repos };
      }
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

/** Drives ProjectsList with real toggle state, the way ProjectsPage does - a click actually
 *  flips `expandedPaths`, which is what the scroll-into-view effect reacts to. `renderList`'s
 *  fixed prop can't exercise that: it never transitions from closed to open. */
function ToggleableList() {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const onToggle = (p: Project) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(p.path)) next.delete(p.path);
      else next.add(p.path);
      return next;
    });
  };
  return <ProjectsList expandedPaths={expandedPaths} onToggle={onToggle} renderExpanded={(p) => <div>Details for {p.name}</div>} />;
}

function renderToggleableList() {
  const client = createQueryClient();
  render(
    <QueryClientProvider client={client}>
      <ToggleableList />
    </QueryClientProvider>,
  );
  return client;
}

/** jsdom doesn't implement scrollIntoView at all; the component itself guards every call with
 *  `?.` for that gap (see ProjectsList.tsx), so this stub is only here to observe the calls. */
function stubScrollIntoView() {
  const scrollIntoView = vi.fn();
  Element.prototype.scrollIntoView = scrollIntoView;
  return scrollIntoView;
}

afterEach(() => {
  vi.unstubAllGlobals();
  delete (Element.prototype as unknown as { scrollIntoView?: unknown }).scrollIntoView;
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

  it("scrolls the row to the top once its panel opens, but not when it closes again", async () => {
    stubApi(true);
    const scrollIntoView = stubScrollIntoView();
    const client = renderToggleableList();

    const openButton = await screen.findByRole("button", { name: "Show details for demo" });
    fireEvent.click(openButton);
    await screen.findByText("Details for demo");

    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "start", behavior: "smooth" });

    scrollIntoView.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Hide details for demo" }));
    // The panel animates closed (see useClosingIds' fallback timer) rather than vanishing the
    // instant the row collapses, so this outlives waitFor's default 1000ms timeout.
    await waitFor(() => expect(screen.queryByText("Details for demo")).not.toBeInTheDocument(), { timeout: 2000 });

    expect(scrollIntoView).not.toHaveBeenCalled();
    client.clear();
  });

  it("doesn't scroll a row that's already expanded on mount", async () => {
    stubApi(true);
    const scrollIntoView = stubScrollIntoView();
    const { client } = renderList([project.path]);

    await screen.findByText("Details for demo");

    expect(scrollIntoView).not.toHaveBeenCalled();
    client.clear();
  });
});

describe("ProjectsList repo columns", () => {
  it("shows the source as a link, with the issue and PR counts", async () => {
    stubApi(true, [githubRepo]);
    const { client } = renderList();

    const link = await screen.findByRole("link", { name: "GitHub" });

    expect(link).toHaveAttribute("href", "https://github.com/acme/demo");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    const row = screen.getByRole("link", { name: "GitHub" }).closest("tr") as HTMLElement;
    expect(within(row).getByText("7")).toBeInTheDocument();
    expect(within(row).getByText("2")).toBeInTheDocument();
    client.clear();
  });

  it("renders the row at once, with dashes, before the repo info arrives", async () => {
    stubApi(true, [githubRepo]);
    const answer = vi.mocked(fetch).getMockImplementation()!;
    // The repo lookup is slow on the server (git, gh): hold its answer while the projects load.
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) =>
        url.startsWith("/api/projects/repos") ? new Promise<Response>(() => {}) : answer(url, init),
      ),
    );
    const { client } = renderList();

    const row = (await screen.findByRole("button", { name: "Show details for demo" })).closest("tr") as HTMLElement;

    expect(within(row).queryByRole("link", { name: "GitHub" })).not.toBeInTheDocument();
    expect(within(row).getAllByText("--").length).toBeGreaterThanOrEqual(3);
    client.clear();
  });

  it("shows dashes and no link for a project without a remote", async () => {
    stubApi(true, [{ path: project.path, host: null, url: null, issues: null, prs: null }]);
    const { client } = renderList();
    await screen.findByRole("button", { name: "Show details for demo" });
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).startsWith("/api/projects/repos"))).toBe(true));

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    client.clear();
  });

  it("links another host by its name and leaves the counts as dashes", async () => {
    stubApi(true, [{ path: project.path, host: "gitlab.com", url: "https://gitlab.com/acme/demo", issues: null, prs: null }]);
    const { client } = renderList();

    const link = await screen.findByRole("link", { name: "gitlab.com" });

    const row = link.closest("tr") as HTMLElement;
    expect(within(row).getAllByText("--").length).toBeGreaterThanOrEqual(2);
    client.clear();
  });

  it("does not toggle the row when the source link is clicked", async () => {
    stubApi(true, [githubRepo]);
    const { client, onToggle } = renderList();
    const link = await screen.findByRole("link", { name: "GitHub" });

    fireEvent.click(link);

    expect(onToggle).not.toHaveBeenCalled();
    client.clear();
  });

  it("shows the source as plain text on a narrow card, which is itself a button", async () => {
    stubApi(true, [githubRepo], true);
    const { client } = renderList();

    const card = await screen.findByRole("button", { name: /demo/ });

    await waitFor(() => expect(within(card).getByText("GitHub")).toBeInTheDocument());
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    client.clear();
  });
});
