import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import type { SessionDetail, SessionResponse } from "../../api/types";
import { SessionDialog } from "./SessionDialog";

// The real chart needs Vega; stand in for it with one button per response that reports a selection.
vi.mock("./TokensChart", () => ({
  TokensChart: ({ turns, onSelect }: { turns: unknown[]; onSelect?: (response: number) => void }) => (
    <div>
      {turns.map((_, index) => (
        <button key={index} type="button" onClick={() => onSelect?.(index + 1)}>
          bar {index + 1}
        </button>
      ))}
    </div>
  ),
}));

let response: SessionResponse;

vi.mock("../../api/queries", () => ({
  LIVE_POLL_MS: 2000,
  useSession: () => ({ data: response, isPending: false, isError: false, refetch: () => {} }),
  useMeta: () => ({ data: { is_local: false } }),
  useDeleteSession: () => ({ mutate: () => {}, isPending: false, isError: false }),
}));

const turn = (context: number) => ({
  message_id: `m${context}`,
  timestamp: null,
  new: 0,
  cache_read: context,
  cache_written: 0,
  output: 1,
  context,
  tools: [],
  cache_miss: false,
});

function detail(withBreakdown: boolean): SessionDetail {
  return {
    turns: [turn(10_000), turn(12_000)],
    compactions: [],
    attribution: { floor: 10_000, current: 12_000, by_tool: [], largest: [] },
    breakdown: withBreakdown
      ? {
          snapshots: [{ position: 0, categories: [{ name: "Skills", tokens: 2_000, items: [{ label: "review", tokens: 2_000 }] }] }],
          turns: [
            { snapshot: 0, growth: [], remainder: 8_000 },
            { snapshot: 0, growth: [{ tool: "Read", tokens: 2_000 }], remainder: 8_000 },
          ],
        }
      : null,
  };
}

function open(withBreakdown: boolean) {
  response = { session_id: "s1", live: false, recap: null, readable: true, detail: detail(withBreakdown) };
  render(<SessionDialog sessionId="s1" onClose={() => {}} />);
}

beforeAll(() => {
  // jsdom has no <dialog> behavior.
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
  };
});

const panel = () => screen.queryByRole("region", { name: /Context breakdown for response/ });

describe("SessionDialog context breakdown", () => {
  it("shows no panel until a bar is selected", () => {
    open(true);

    expect(panel()).not.toBeInTheDocument();
  });

  it("pins a panel for the selected response, with its categories collapsed", () => {
    open(true);

    fireEvent.click(screen.getByRole("button", { name: "bar 2" }));

    expect(panel()).toHaveAccessibleName("Context breakdown for response 2");
    expect(screen.getByText("Response 2: 12,000 tokens")).toBeInTheDocument();
    expect((screen.getByText("Skills").closest("details") as HTMLDetailsElement).open).toBe(false);
  });

  it("replaces the panel's response when another bar is selected, collapsing it again", () => {
    open(true);
    fireEvent.click(screen.getByRole("button", { name: "bar 2" }));
    (screen.getByText("Skills").closest("details") as HTMLDetailsElement).open = true;

    fireEvent.click(screen.getByRole("button", { name: "bar 1" }));

    expect(panel()).toHaveAccessibleName("Context breakdown for response 1");
    expect((screen.getByText("Skills").closest("details") as HTMLDetailsElement).open).toBe(false);
  });

  it("removes the panel when dismissed", () => {
    open(true);
    fireEvent.click(screen.getByRole("button", { name: "bar 1" }));

    fireEvent.click(screen.getByRole("button", { name: "Dismiss breakdown" }));

    expect(panel()).not.toBeInTheDocument();
  });

  it("shows no panel when the server sent no breakdown", () => {
    open(false);

    fireEvent.click(screen.getByRole("button", { name: "bar 1" }));

    expect(panel()).not.toBeInTheDocument();
    expect(screen.getByText("Tokens per response")).toBeInTheDocument();
  });
});
