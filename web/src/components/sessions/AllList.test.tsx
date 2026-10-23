import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { TranscriptItem } from "../../api/types";
import { AllList } from "./AllList";

function item(id: string, worktree: string): TranscriptItem {
  return {
    session_id: id,
    project: "the-ledger",
    title: `title-${id}`,
    started_at: null,
    updated_at: null,
    message_count: 1,
    cost: 0,
    cost_source: "exact",
    unpriced_models: [],
    cost_state_flagged: false,
    context: null,
    model: "",
    used_openspec: false,
    version: "",
    git_branch: "main",
    worktree,
    live: false,
  };
}

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
    vi.fn(async () => {
      const body = {
        items: [item("a", "add-wiki-docs"), item("b", "")],
        total: 2,
        options: { projects: ["the-ledger"], versions: [], branches: ["main"], worktrees: ["add-wiki-docs"] },
      };
      return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
    }),
  );
}

function renderList() {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <AllList onSelect={() => undefined} />
    </QueryClientProvider>,
  );
}

const lastUrl = () => new URL(vi.mocked(fetch).mock.calls.at(-1)![0] as string, "http://x");

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the All list's Worktree column", () => {
  it("shows the worktree name, or -- when the session ran in none", async () => {
    stubApi();
    renderList();

    const rows = await screen.findAllByRole("row");
    const cells = (row: HTMLElement) => within(row).getAllByRole("cell").map((c) => c.textContent);
    expect(cells(rows[1])).toContain("add-wiki-docs");
    expect(cells(rows[2])).not.toContain("add-wiki-docs");
    expect(cells(rows[2]).filter((c) => c === "--").length).toBeGreaterThan(0);
    expect(screen.getByRole("columnheader", { name: /Worktree/ })).toBeInTheDocument();
  });

  it("sorts by worktree when its header is clicked", async () => {
    stubApi();
    renderList();
    fireEvent.click(await screen.findByRole("button", { name: /Worktree/ }));

    await waitFor(() => expect(lastUrl().searchParams.get("sort")).toBe("worktree"));
  });

  it("filters by the chosen worktree", async () => {
    stubApi();
    renderList();
    fireEvent.click(await screen.findByRole("button", { name: /^Worktree/ }));
    fireEvent.click(await screen.findByRole("checkbox", { name: "add-wiki-docs" }));

    await waitFor(() => expect(lastUrl().searchParams.getAll("worktree")).toEqual(["add-wiki-docs"]));
  });
});
