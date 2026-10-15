import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { REMAINDER_NAME, REMAINDER_NOTE, type BreakdownRow } from "../../lib/contextBreakdown";
import { ContextBreakdownPanel } from "./ContextBreakdownPanel";

const rows: BreakdownRow[] = [
  { name: REMAINDER_NAME, tokens: 15_800, estimated: false, items: [], note: REMAINDER_NOTE },
  {
    name: "Skills",
    tokens: 6_700,
    estimated: true,
    items: [
      { label: "review", tokens: 4_000 },
      { label: "deploy", tokens: 2_700 },
    ],
  },
  { name: "Read", tokens: 5_000, estimated: false, items: [] },
];

const renderPanel = (onDismiss = () => {}) =>
  render(<ContextBreakdownPanel response={2} context={28_300} rows={rows} onDismiss={onDismiss} />);

describe("ContextBreakdownPanel", () => {
  it("lists every category with tokens and its share of the response's context", () => {
    renderPanel();

    expect(screen.getByText("Response 2: 28,300 tokens")).toBeInTheDocument();
    const skills = screen.getByText("Skills").closest("summary") as HTMLElement;
    expect(within(skills).getByText("~6,700")).toBeInTheDocument();
    expect(within(skills).getByText("24%")).toBeInTheDocument();
    expect(screen.getByText("15,800")).toBeInTheDocument();
    expect(screen.getByText("56%")).toBeInTheDocument();
  });

  it("marks estimates and leaves exact figures unmarked", () => {
    renderPanel();

    expect(screen.getByText("~6,700")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
    expect(screen.queryByText("~5,000")).not.toBeInTheDocument();
  });

  it("says what the remainder row contains", () => {
    renderPanel();

    expect(screen.getByText(REMAINDER_NOTE)).toBeInTheDocument();
  });

  it("starts with every category collapsed and shows items once one is expanded", () => {
    renderPanel();
    const details = screen.getByText("Skills").closest("details") as HTMLDetailsElement;

    expect(details.open).toBe(false);
    details.open = true;
    expect(within(details).getByText("review")).toBeInTheDocument();
    expect(within(details).getByText("~4,000")).toBeInTheDocument();
  });

  it("only offers to expand categories that have items", () => {
    renderPanel();

    expect(document.querySelectorAll("details")).toHaveLength(1);
  });

  it("calls onDismiss from its dismiss control", () => {
    const onDismiss = vi.fn();
    renderPanel(onDismiss);

    fireEvent.click(screen.getByRole("button", { name: "Dismiss breakdown" }));

    expect(onDismiss).toHaveBeenCalledOnce();
  });
});
