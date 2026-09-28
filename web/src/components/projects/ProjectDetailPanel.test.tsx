import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { Project } from "../../api/types";
import { ProjectDetailPanel } from "./ProjectDetailPanel";

// The real charts lazy-load vega-embed, which has nothing to draw on in jsdom; what matters here is
// which data each one is handed.
vi.mock("../overview/GroupDonutChart", () => ({
  GroupDonutChart: (props: { groups: { group: string }[]; groupLabel: string }) => (
    <div data-testid="donut">
      {props.groupLabel}:{props.groups.map((g) => g.group).join(",")}
    </div>
  ),
}));
vi.mock("../overview/GroupBarChart", () => ({
  GroupBarChart: (props: { groupLabel: string }) => <div data-testid="bars">{props.groupLabel}</div>,
}));
vi.mock("../overview/ActivityLineChart", () => ({
  ActivityLineChart: () => <div data-testid="activity" />,
}));

const project: Project = {
  path: "C:\\repos\\demo",
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

const populated = {
  range: "All time",
  empty: false,
  available_ranges: ["All time", "Past week", "Past year"],
  summary: {},
  groups: [{ group: "main", sessions: 2, messages: 4, cost: 1, share: 100, messages_pct: 100, cost_pct: 100 }],
  group_order: ["main"],
  activity: [],
};

interface ApiOptions {
  isLocal?: boolean;
  overview?: unknown;
  /** Answers `DELETE /api/projects`; the default succeeds. */
  deleteResponse?: () => Response | Promise<Response>;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function stubApi({ isLocal = true, overview = populated, deleteResponse }: ApiOptions = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.startsWith("/api/meta")) return json({ refreshed_at: null, is_local: isLocal });
      if (url.startsWith("/api/overview")) return json(overview);
      if (url.startsWith("/api/projects") && init?.method === "DELETE") {
        return deleteResponse ? deleteResponse() : json({ deleted: project.path });
      }
      return json({ projects: [project] });
    }),
  );
}

function renderPanel(onDeleted = vi.fn()) {
  const client = createQueryClient();
  const view = render(
    <QueryClientProvider client={client}>
      <ProjectDetailPanel project={project} scrollKey={0} onDeleted={onDeleted} />
    </QueryClientProvider>,
  );
  const dialog = view.container.querySelector("dialog") as HTMLDialogElement;
  return { ...view, client, dialog, onDeleted };
}

const calls = (prefix: string) =>
  vi.mocked(fetch).mock.calls.filter(([url]) => (url as string).startsWith(prefix));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ProjectDetailPanel charts", () => {
  it("renders the three charts, grouped by branch, for that project", async () => {
    stubApi();
    const { client } = renderPanel();

    expect(await screen.findByTestId("donut")).toHaveTextContent("branch:main");
    expect(screen.getByTestId("bars")).toHaveTextContent("branch");
    expect(screen.getByTestId("activity")).toBeInTheDocument();

    const url = calls("/api/overview")[0][0] as string;
    const params = new URL(url, "http://x").searchParams;
    expect(params.get("project")).toBe(project.path);
    expect(params.get("group_by")).toBe("branch");
    expect(params.get("bucket_minutes")).toBe("60");
    expect(params.get("range")).toBe("All time");
    client.clear();
  });

  it("re-queries the same project when the range changes", async () => {
    stubApi();
    const { client } = renderPanel();
    await screen.findByTestId("donut");

    fireEvent.click(screen.getByRole("radio", { name: "Past week" }));

    await waitFor(() => {
      const last = calls("/api/overview").at(-1)![0] as string;
      const params = new URL(last, "http://x").searchParams;
      expect(params.get("range")).toBe("Past week");
      expect(params.get("project")).toBe(project.path);
    });
    client.clear();
  });

  it("says so, instead of drawing empty charts, when the range has no sessions", async () => {
    stubApi({ overview: { range: "All time", empty: true, available_ranges: [] } });
    const { client } = renderPanel();

    expect(await screen.findByText("No sessions found for this project.")).toBeInTheDocument();
    expect(screen.queryByTestId("donut")).not.toBeInTheDocument();
    client.clear();
  });

  it("disables the time ranges that have no sessions for the project", async () => {
    stubApi({ overview: populated });
    const { client } = renderPanel();
    await screen.findByTestId("donut");

    expect(screen.getByRole("radio", { name: "All time" })).toBeEnabled();
    expect(screen.getByRole("radio", { name: "Past week" })).toBeEnabled();
    expect(screen.getByRole("radio", { name: "Today" })).toBeDisabled();
    expect(screen.getByRole("radio", { name: "Past month" })).toBeDisabled();
    client.clear();
  });

  it("names the range in the empty message for any other range", async () => {
    stubApi({ overview: { range: "Today", empty: true, available_ranges: ["All time", "Today"] } });
    const { client } = renderPanel();
    await screen.findByText("No sessions found for this project.");

    fireEvent.click(screen.getByRole("radio", { name: "Today" }));

    expect(await screen.findByText("No sessions found for today.")).toBeInTheDocument();
    client.clear();
  });
});

describe("ProjectDetailPanel delete", () => {
  it("offers no delete control from another device", async () => {
    stubApi({ isLocal: false });
    const { client } = renderPanel();
    await screen.findByTestId("donut");
    await waitFor(() => expect(calls("/api/meta").length).toBeGreaterThan(0));
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    client.clear();
  });

  it("opens a confirmation naming the path, without deleting yet", async () => {
    stubApi();
    const { client, dialog } = renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Delete project" }));

    expect(dialog.open).toBe(true);
    expect(dialog).toHaveTextContent(project.path);
    expect(dialog).toHaveTextContent("This cannot be undone.");
    expect(calls("/api/projects").filter(([, init]) => init?.method === "DELETE")).toHaveLength(0);
    client.clear();
  });

  it("closes without deleting when cancelled", async () => {
    stubApi();
    const { client, dialog, onDeleted } = renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Delete project" }));

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(dialog.open).toBe(false);
    expect(onDeleted).not.toHaveBeenCalled();
    expect(calls("/api/projects").filter(([, init]) => init?.method === "DELETE")).toHaveLength(0);
    client.clear();
  });

  it("deletes that project's path, then closes the modal and reports it", async () => {
    stubApi();
    const { client, dialog, onDeleted } = renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Delete project" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
    const [url, init] = calls("/api/projects").find(([, i]) => i?.method === "DELETE")!;
    expect(new URL(url as string, "http://x").searchParams.get("path")).toBe(project.path);
    expect(init?.method).toBe("DELETE");
    expect(dialog.open).toBe(false);
    client.clear();
  });

  it("keeps the modal open and shows the server's error when the delete fails", async () => {
    stubApi({ deleteResponse: () => json({ detail: "Deleting a project needs a local request." }, 403) });
    const { client, dialog, onDeleted } = renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Delete project" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Deleting a project needs a local request.");
    expect(dialog.open).toBe(true);
    expect(onDeleted).not.toHaveBeenCalled();

    // Cancelling clears the stale error, so the next attempt doesn't open on it.
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete project" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    client.clear();
  });

  it("disables the modal's controls while the delete is in flight", async () => {
    let finish: (response: Response) => void = () => {};
    stubApi({ deleteResponse: () => new Promise<Response>((resolve) => (finish = resolve)) });
    const { client, dialog } = renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Delete project" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    const busy = await screen.findByRole("button", { name: "Deleting…" });
    expect(busy).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
    expect(dialog.open).toBe(true);

    finish(json({ deleted: project.path }));
    await waitFor(() => expect(dialog.open).toBe(false));
    client.clear();
  });
});
