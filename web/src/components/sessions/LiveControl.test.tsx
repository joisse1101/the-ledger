import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { LiveSession } from "../../api/types";
import { LiveControl } from "./LiveControl";

const REMOTE_OFF = { enabled: false, expires_at: null, state: "off", step: null, reason: null };

function session(lastAutoApproved: LiveSession["last_auto_approved"]): LiveSession {
  return {
    session_id: "abc",
    pid: 1,
    name: "n",
    project: "p",
    title: "t",
    status: "idle",
    kind: "interactive",
    started_at: null,
    updated_at: null,
    last_message: "",
    first_prompt: "",
    context: null,
    pending_decision: null,
    auto_approve: true,
    last_auto_approved: lastAutoApproved,
  };
}

function renderControl(live: LiveSession) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const body = url.endsWith("/pending-decision")
        ? { pending_decision: null }
        : { refreshed_at: null, is_local: true, remote_mode: REMOTE_OFF, relay_hook_seen: true };
      return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
    }),
  );
  render(
    <QueryClientProvider client={createQueryClient()}>
      <LiveControl sessionId="abc" session={live} liveLoaded />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LiveControl auto-approve line", () => {
  it("names the tool of the latest auto-approved prompt", async () => {
    renderControl(session({ tool_name: "Edit", at: "2026-01-01T12:00:00+00:00" }));
    expect(await screen.findByText(/Last auto-approved: Edit at/)).toBeInTheDocument();
  });

  it("has no such line when nothing was auto-approved", async () => {
    renderControl(session(null));
    await screen.findByText(/Nothing is waiting on you/);
    expect(screen.queryByText(/Last auto-approved/)).not.toBeInTheDocument();
  });
});
