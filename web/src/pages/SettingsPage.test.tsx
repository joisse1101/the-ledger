import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../api/queryClient";
import { SettingsPage } from "./SettingsPage";

const BUILT_IN = { path: ".claude/worktrees", built_in: true };

interface World {
  isLocal: boolean;
  userFolders: string[];
  maxProjects: number;
  /** Folders the fake server refuses, with its reason. */
  refused: Record<string, string>;
  /** The body of each save, as the server received it. */
  puts: { worktree_folders?: string[]; widget?: { max_projects: number } }[];
  /** While set, a save waits for it, so a test can look at the pending state. */
  gate: Promise<void> | null;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function settingsBody(world: World) {
  return {
    worktree_folders: [BUILT_IN, ...world.userFolders.map((path) => ({ path, built_in: false }))],
    widget: { max_projects: world.maxProjects },
  };
}

function stubServer(world: World) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      const method = (init?.method ?? "GET").toUpperCase();
      if (input === "/api/meta") {
        return json({
          refreshed_at: null,
          is_local: world.isLocal,
          remote_mode: { enabled: false, expires_at: null, state: "off", step: null, reason: null },
        });
      }
      if (input === "/api/settings" && method === "GET") {
        return world.isLocal ? json(settingsBody(world)) : json({ detail: "settings require a local request" }, 403);
      }
      if (input === "/api/settings" && method === "PUT") {
        const body = JSON.parse(String(init?.body)) as World["puts"][number];
        world.puts.push(body);
        await world.gate;
        const bad = body.worktree_folders?.find((folder) => folder in world.refused);
        if (bad !== undefined) return json({ detail: world.refused[bad] }, 422);
        const maxProjects = body.widget?.max_projects;
        if (maxProjects !== undefined && !(Number.isInteger(maxProjects) && maxProjects >= 1 && maxProjects <= 10)) {
          return json({ detail: "Must be a whole number from 1 to 10." }, 422);
        }
        if (body.worktree_folders) world.userFolders = body.worktree_folders;
        if (maxProjects !== undefined) world.maxProjects = maxProjects;
        return json(settingsBody(world));
      }
      return json({ detail: "unexpected" }, 500);
    }),
  );
}

function renderPage(world: World) {
  stubServer(world);
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={["/settings"]}>
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/" element={<div>home page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

let world: World;
beforeEach(() => {
  world = { isLocal: true, userFolders: [], maxProjects: 5, refused: {}, puts: [], gate: null };
});
afterEach(() => vi.unstubAllGlobals());

describe("SettingsPage", () => {
  it("lists the built-in folder with no way to remove it", async () => {
    renderPage(world);

    const list = await screen.findByRole("list", { name: "Worktree folders" });
    const row = await within(list).findByText(".claude/worktrees");
    expect(row.closest("li")).toHaveTextContent("Built in");
    expect(within(list).queryByRole("button", { name: /remove/i })).not.toBeInTheDocument();
  });

  it("adds a folder at once and clears the input", async () => {
    renderPage(world);

    fireEvent.change(await screen.findByLabelText("Add a folder"), { target: { value: ".trees" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    const list = screen.getByRole("list", { name: "Worktree folders" });
    expect(await within(list).findByText(".trees")).toBeInTheDocument();
    expect(world.puts).toEqual([{ worktree_folders: [".trees"] }]);
    expect(screen.getByLabelText("Add a folder")).toHaveValue("");
  });

  it("keeps the folders already listed when adding another", async () => {
    world.userFolders = [".trees"];
    renderPage(world);

    fireEvent.change(await screen.findByLabelText("Add a folder"), { target: { value: "tools/wt" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(world.puts).toEqual([{ worktree_folders: [".trees", "tools/wt"] }]));
  });

  it("removes a folder at once", async () => {
    world.userFolders = [".trees", "tools/wt"];
    renderPage(world);

    fireEvent.click(await screen.findByRole("button", { name: "Remove .trees" }));

    const list = screen.getByRole("list", { name: "Worktree folders" });
    await waitFor(() => expect(within(list).queryByText(".trees")).not.toBeInTheDocument());
    expect(world.puts).toEqual([{ worktree_folders: ["tools/wt"] }]);
    expect(within(list).getByText("tools/wt")).toBeInTheDocument();
  });

  it("shows the server's reason for a rejected folder and keeps the list and the input", async () => {
    world.refused = { "../shared": "'../shared': Must be a path inside the repo, with no '.' or '..' parts." };
    renderPage(world);

    fireEvent.change(await screen.findByLabelText("Add a folder"), { target: { value: "../shared" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Must be a path inside the repo");
    expect(screen.getByLabelText("Add a folder")).toHaveValue("../shared");
    const list = screen.getByRole("list", { name: "Worktree folders" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
  });

  it("shows a pending state while the server re-files sessions", async () => {
    let release: () => void = () => {};
    world.gate = new Promise<void>((resolve) => (release = resolve));
    renderPage(world);

    fireEvent.change(await screen.findByLabelText("Add a folder"), { target: { value: ".trees" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Saving");
    expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
    release();
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
  });

  it("shows the widget's projects-shown number, 5 until set", async () => {
    renderPage(world);

    const input = await screen.findByLabelText("Projects shown (1 to 10)");
    await waitFor(() => expect(input).toHaveValue(5));
  });

  it("saves a new number on its own, without touching the folders", async () => {
    world.userFolders = [".trees"];
    renderPage(world);

    const input = await screen.findByLabelText("Projects shown (1 to 10)");
    await waitFor(() => expect(input).toHaveValue(5));
    fireEvent.change(input, { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(world.maxProjects).toBe(3));
    expect(world.puts).toEqual([{ widget: { max_projects: 3 } }]);
    expect(world.userFolders).toEqual([".trees"]);
    await waitFor(() => expect(screen.getByLabelText("Projects shown (1 to 10)")).toHaveValue(3));
  });

  it("shows the server's reason for a rejected number and keeps what was typed", async () => {
    renderPage(world);

    const input = await screen.findByLabelText("Projects shown (1 to 10)");
    await waitFor(() => expect(input).toHaveValue(5));
    fireEvent.change(input, { target: { value: "11" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("whole number from 1 to 10");
    expect(screen.getByLabelText("Projects shown (1 to 10)")).toHaveValue(11);
    expect(world.maxProjects).toBe(5);
  });

  it("leaves the number alone when a folder is added", async () => {
    world.maxProjects = 3;
    renderPage(world);

    fireEvent.change(await screen.findByLabelText("Add a folder"), { target: { value: ".trees" } });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(world.puts).toEqual([{ worktree_folders: [".trees"] }]));
    expect(world.maxProjects).toBe(3);
    expect(screen.getByLabelText("Projects shown (1 to 10)")).toHaveValue(3);
  });

  it("sends a device that is not local to the home page without asking for settings", async () => {
    world.isLocal = false;
    renderPage(world);

    expect(await screen.findByText("home page")).toBeInTheDocument();
    const urls = vi.mocked(fetch).mock.calls.map(([input]) => input);
    expect(urls).not.toContain("/api/settings");
  });
});
