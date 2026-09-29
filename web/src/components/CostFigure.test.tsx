import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CostFigure } from "./CostFigure";

describe("CostFigure", () => {
  it("renders an exact cost plainly, with no asterisk or tooltip", () => {
    render(<CostFigure label="$3.34" source="exact" />);

    expect(screen.getByText("$3.34")).toBeInTheDocument();
    expect(screen.queryByText("$3.34*")).not.toBeInTheDocument();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("renders a missing source (no cost source at all) plainly too", () => {
    render(<CostFigure label="--" source={null} />);

    expect(screen.getByText("--")).toBeInTheDocument();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("marks an estimated cost with an asterisk and an explanatory tooltip", () => {
    render(<CostFigure label="$0.23" source="estimated" />);

    expect(screen.getByText("$0.23*")).toBeInTheDocument();
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Claude Code hasn't reported a final cost for this session yet",
    );
  });

  it("threads named unpriced models into the tooltip", () => {
    render(
      <CostFigure label="$0.23" source="estimated" unpricedModels={["claude-opus-5-5"]} />,
    );

    expect(screen.getByRole("tooltip")).toHaveTextContent("claude-opus-5-5");
  });

  it("threads cost_state_flagged into the tooltip when no model was named", () => {
    render(<CostFigure label="$0.23" source="estimated" costStateFlagged={true} />);

    expect(screen.getByRole("tooltip")).toHaveTextContent("Claude Code flagged part of this session's cost");
  });
});
