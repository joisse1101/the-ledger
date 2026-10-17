import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "../../api/queryClient";
import type { LiveSession } from "../../api/types";
import { AutoApproveControl } from "./AutoApproveControl";

const REMOTE_OFF = { enabled: false, expires_at: null, state: "off", step: null, reason: null };

function session(autoApprove: boolean): LiveSession {
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
    auto_approve: autoApprove,
    last_auto_approved: null,
  };
}

function stubApi({ isLocal, hookSeen }: { isLocal: boolean; hookSeen: boolean }) {
  const fetchMock = vi.fn(async (url: string) => {
    const body = url.endsWith("/auto-approve")
      ? { auto_approve: true }
      : { refreshed_at: null, is_local: isLocal, remote_mode: REMOTE_OFF, relay_hook_seen: hookSeen };
    return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderControl(live: LiveSession | null) {
  render(
    <QueryClientProvider client={createQueryClient()}>
      <AutoApproveControl session={live} />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AutoApproveControl", () => {
  it("shows nothing before a prompt has been relayed", async () => {
    const fetchMock = stubApi({ isLocal: true, hookSeen: false });
    renderControl(session(true));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(screen.queryByText(/Auto-approve/)).not.toBeInTheDocument();
  });

  it("is a switch on the machine running the app, and flipping it posts enabled: true", async () => {
    const fetchMock = stubApi({ isLocal: true, hookSeen: true });
    renderControl(session(false));

    const toggle = await screen.findByRole("switch", { name: /Auto-approve/ });
    expect(toggle).not.toBeChecked();
    fireEvent.click(toggle);

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(([url]) => url === "/api/sessions/abc/auto-approve");
      expect(post).toBeDefined();
    });
  });

  it("is read-only text on another device, and only while it is on", async () => {
    stubApi({ isLocal: false, hookSeen: true });
    renderControl(session(true));

    expect(await screen.findByText("Auto-approve on")).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });

  it("shows nothing on another device while it is off", async () => {
    const fetchMock = stubApi({ isLocal: false, hookSeen: true });
    renderControl(session(false));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(screen.queryByText("Auto-approve on")).not.toBeInTheDocument();
  });
});
