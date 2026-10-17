import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { LiveSession } from "../../api/types";
import { LiveList } from "./LiveList";

const REMOTE_OFF = { enabled: false, expires_at: null, state: "off", step: null, reason: null };

function session(id: string, autoApprove: boolean): LiveSession {
  return {
    session_id: id,
    pid: 1,
    name: `name-${id}`,
    project: `proj-${id}`,
    title: `title-${id}`,
    status: "idle",
    kind: "interactive",
    started_at: null,
    updated_at: null,
    last_message: "",
    first_prompt: "",
    context: null,
    pending_decision: null,
    auto_approve: autoApprove,
    last_auto_approved: null,
  };
}

/** jsdom has no matchMedia; every query "matches", so the list renders as the wide table. */
function stubWideViewport() {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: true,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

function stubApi(hookSeen: boolean) {
  stubWideViewport();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const body =
        url === "/api/live"
          ? { sessions: [session("on", true), session("off", false)] }
          : { refreshed_at: null, is_local: true, remote_mode: REMOTE_OFF, relay_hook_seen: hookSeen };
      return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
    }),
  );
}

function renderList() {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <LiveList onSelect={() => undefined} />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the Live list's Auto-approve column", () => {
  it("is absent before a prompt has been relayed", async () => {
    stubApi(false);
    renderList();

    await screen.findByText("proj-on");
    expect(screen.queryByRole("columnheader", { name: "Auto-approve" })).not.toBeInTheDocument();
  });

  it("marks only the sessions that have it on, once a prompt has been relayed", async () => {
    stubApi(true);
    renderList();

    await screen.findByRole("columnheader", { name: "Auto-approve" });
    const rowOf = (text: string) => screen.getByText(text).closest("tr") as HTMLElement;
    expect(within(rowOf("proj-on")).getByText("On")).toBeInTheDocument();
    expect(within(rowOf("proj-off")).queryByText("On")).not.toBeInTheDocument();
  });
});
