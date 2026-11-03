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
  afkMinutes: number;
  breakMinutes: number;
  /** What the fake server answers to Open folder: a path on success, or a failure message. */
  openResult: { path: string } | { detail: string };
  /** Folders the fake server refuses, with its reason. */
  refused: Record<string, string>;
  /** The body of each save, as the server received it. */
  puts: { worktree_folders?: string[]; widget?: { max_projects?: number; afk_minutes?: number; break_minutes?: number } }[];
  /** How many times the folder was asked to open. */
  opens: number;
  /** While set, a save waits for it, so a test can look at the pending state. */
  gate: Promise<void> | null;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function settingsBody(world: World) {
  return {
    worktree_folders: [BUILT_IN, ...world.userFolders.map((path) => ({ path, built_in: false }))],
    widget: { max_projects: world.maxProjects, afk_minutes: world.afkMinutes, break_minutes: world.breakMinutes },
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
        const breakMinutes = body.widget?.break_minutes;
        if (breakMinutes !== undefined && !(Number.isInteger(breakMinutes) && breakMinutes >= 1 && breakMinutes <= 240)) {
          return json({ detail: "Must be a whole number from 1 to 240." }, 422);
        }
        const afkMinutes = body.widget?.afk_minutes;
        if (afkMinutes !== undefined && !(Number.isInteger(afkMinutes) && afkMinutes >= 1 && afkMinutes <= 240)) {
          return json({ detail: "Must be a whole number from 1 to 240." }, 422);
        }
        if (body.worktree_folders) world.userFolders = body.worktree_folders;
        if (maxProjects !== undefined) world.maxProjects = maxProjects;
        if (afkMinutes !== undefined) world.afkMinutes = afkMinutes;
        if (breakMinutes !== undefined) world.breakMinutes = breakMinutes;
        return json(settingsBody(world));
      }
      if (input === "/api/widget/workouts/open" && method === "POST") {
        world.opens += 1;
        return "path" in world.openResult ? json(world.openResult) : json(world.openResult, 500);
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
  world = {
    isLocal: true, userFolders: [], maxProjects: 5, afkMinutes: 30,
    breakMinutes: 60,
    openResult: { path: "C:/ledger/widget/workouts/mine" },
    refused: {},
    puts: [],
    opens: 0,
    gate: null,
  };
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

  it("shows the AFK minutes, 30 until set", async () => {
    renderPage(world);

    const input = await screen.findByLabelText("AFK minutes (1 to 240)");
    await waitFor(() => expect(input).toHaveValue(30));
  });

  it("saves new AFK minutes on their own, leaving the folders and the projects number", async () => {
    world.userFolders = [".trees"];
    world.maxProjects = 3;
    renderPage(world);

    const input = await screen.findByLabelText("AFK minutes (1 to 240)");
    await waitFor(() => expect(input).toHaveValue(30));
    fireEvent.change(input, { target: { value: "10" } });
    fireEvent.click(screen.getByRole("button", { name: "Save AFK minutes" }));

    await waitFor(() => expect(world.afkMinutes).toBe(10));
    expect(world.puts).toEqual([{ widget: { afk_minutes: 10 } }]);
    expect(world.userFolders).toEqual([".trees"]);
    expect(world.maxProjects).toBe(3);
    await waitFor(() => expect(screen.getByLabelText("AFK minutes (1 to 240)")).toHaveValue(10));
  });

  it.each(["0", "241", "7.5"])("shows the server's reason for %s AFK minutes and keeps what was typed", async (typed) => {
    renderPage(world);

    const input = await screen.findByLabelText("AFK minutes (1 to 240)");
    await waitFor(() => expect(input).toHaveValue(30));
    fireEvent.change(input, { target: { value: typed } });
    fireEvent.click(screen.getByRole("button", { name: "Save AFK minutes" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("whole number from 1 to 240");
    expect(screen.getByLabelText("AFK minutes (1 to 240)")).toHaveValue(Number(typed));
    expect(world.afkMinutes).toBe(30);
  });

  it("leaves the AFK minutes alone when the projects number is saved", async () => {
    world.afkMinutes = 10;
    renderPage(world);

    const input = await screen.findByLabelText("Projects shown (1 to 10)");
    await waitFor(() => expect(input).toHaveValue(5));
    fireEvent.change(input, { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(world.maxProjects).toBe(3));
    expect(world.puts).toEqual([{ widget: { max_projects: 3 } }]);
    expect(world.afkMinutes).toBe(10);
    expect(screen.getByLabelText("AFK minutes (1 to 240)")).toHaveValue(10);
  });

  it("shows the break minutes, 60 until set", async () => {
    renderPage(world);

    const input = await screen.findByLabelText("Break minutes (1 to 240)");
    await waitFor(() => expect(input).toHaveValue(60));
  });

  it("saves new break minutes on their own, leaving the other settings", async () => {
    world.userFolders = [".trees"];
    world.maxProjects = 3;
    world.afkMinutes = 10;
    renderPage(world);

    const input = await screen.findByLabelText("Break minutes (1 to 240)");
    await waitFor(() => expect(input).toHaveValue(60));
    fireEvent.change(input, { target: { value: "45" } });
    fireEvent.click(screen.getByRole("button", { name: "Save break minutes" }));

    await waitFor(() => expect(world.breakMinutes).toBe(45));
    expect(world.puts).toEqual([{ widget: { break_minutes: 45 } }]);
    expect(world.userFolders).toEqual([".trees"]);
    expect(world.maxProjects).toBe(3);
    expect(world.afkMinutes).toBe(10);
    await waitFor(() => expect(screen.getByLabelText("Break minutes (1 to 240)")).toHaveValue(45));
  });

  it.each(["0", "241", "7.5"])("shows the server's reason for %s break minutes and keeps what was typed", async (typed) => {
    renderPage(world);

    const input = await screen.findByLabelText("Break minutes (1 to 240)");
    await waitFor(() => expect(input).toHaveValue(60));
    fireEvent.change(input, { target: { value: typed } });
    fireEvent.click(screen.getByRole("button", { name: "Save break minutes" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("whole number from 1 to 240");
    expect(screen.getByLabelText("Break minutes (1 to 240)")).toHaveValue(Number(typed));
    expect(world.breakMinutes).toBe(60);
  });

  it("shows the personal folder's path and asks the server to open it", async () => {
    renderPage(world);

    expect(await screen.findByText("widget/workouts/mine")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open folder" }));

    await waitFor(() => expect(world.opens).toBe(1));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a message with the folder's path when opening fails", async () => {
    world.openResult = { detail: "Could not open C:/ledger/widget/workouts/mine." };
    renderPage(world);

    fireEvent.click(await screen.findByRole("button", { name: "Open folder" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("C:/ledger/widget/workouts/mine");
  });

  it("sends a device that is not local to the home page without asking for settings", async () => {
    world.isLocal = false;
    renderPage(world);

    expect(await screen.findByText("home page")).toBeInTheDocument();
    const urls = vi.mocked(fetch).mock.calls.map(([input]) => input);
    expect(urls).not.toContain("/api/settings");
  });
});
