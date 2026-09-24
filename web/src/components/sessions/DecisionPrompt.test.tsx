import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PendingDecision } from "../../api/types";
import { DecisionPrompt } from "./DecisionPrompt";

const bash: PendingDecision = { id: "p1", tool_name: "Bash", tool_input: { command: "rm -rf build" } };

const question: PendingDecision = {
  id: "p2",
  tool_name: "AskUserQuestion",
  tool_input: {
    questions: [
      { question: "Which database?", header: "DB", options: [{ label: "sqlite" }, { label: "postgres" }] },
      { question: "Which extras?", options: [{ label: "auth" }, { label: "logs" }], multiSelect: true },
    ],
  },
};

describe("a permission prompt", () => {
  it("shows the tool and its input, and Approve sends allow", () => {
    const onAnswer = vi.fn();
    render(<DecisionPrompt decision={bash} busy={false} onAnswer={onAnswer} />);

    expect(screen.getByText("Bash")).toBeInTheDocument();
    expect(screen.getByText(/rm -rf build/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(onAnswer).toHaveBeenCalledWith({ decision: "allow" });
  });

  it("Deny asks for an optional reason, and sends it trimmed", () => {
    const onAnswer = vi.fn();
    render(<DecisionPrompt decision={bash} busy={false} onAnswer={onAnswer} />);

    fireEvent.click(screen.getByRole("button", { name: "Deny" }));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "  not that dir " } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm deny" }));
    expect(onAnswer).toHaveBeenCalledWith({ decision: "deny", reason: "not that dir" });
  });

  it("Deny with no reason sends no reason", () => {
    const onAnswer = vi.fn();
    render(<DecisionPrompt decision={bash} busy={false} onAnswer={onAnswer} />);

    fireEvent.click(screen.getByRole("button", { name: "Deny" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm deny" }));
    expect(onAnswer).toHaveBeenCalledWith({ decision: "deny" });
  });

  it("disables the buttons while an answer is on its way", () => {
    render(<DecisionPrompt decision={bash} busy onAnswer={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Deny" })).toBeDisabled();
  });
});

describe("a question prompt", () => {
  it("keeps Send disabled until every question is answered, then sends the answers map", () => {
    const onAnswer = vi.fn();
    render(<DecisionPrompt decision={question} busy={false} onAnswer={onAnswer} />);
    const send = screen.getByRole("button", { name: "Send answer" });
    expect(send).toBeDisabled();

    fireEvent.click(screen.getByRole("radio", { name: "postgres" }));
    expect(send).toBeDisabled(); // the multi-select still has nothing

    fireEvent.click(screen.getByRole("checkbox", { name: "auth" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "logs" }));
    expect(send).toBeEnabled();
    fireEvent.click(send);

    expect(onAnswer).toHaveBeenCalledWith({
      decision: "answer",
      answers: { "Which database?": "postgres", "Which extras?": ["auth", "logs"] },
    });
  });

  it("takes free text for Other, and won't send it blank", () => {
    const onAnswer = vi.fn();
    render(<DecisionPrompt decision={question} busy={false} onAnswer={onAnswer} />);

    fireEvent.click(screen.getByRole("radio", { name: "Other" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "auth" }));
    expect(screen.getByRole("button", { name: "Send answer" })).toBeDisabled(); // Other ticked, still blank

    fireEvent.change(screen.getByLabelText("Your own answer to: Which database?"), { target: { value: " duckdb " } });
    fireEvent.click(screen.getByRole("checkbox", { name: "Other" }));
    fireEvent.change(screen.getByLabelText("Your own answer to: Which extras?"), { target: { value: "metrics" } });
    fireEvent.click(screen.getByRole("button", { name: "Send answer" }));

    expect(onAnswer).toHaveBeenCalledWith({
      decision: "answer",
      answers: { "Which database?": "duckdb", "Which extras?": ["auth", "metrics"] },
    });
  });

  it("says a question with no readable options must be answered in the terminal", () => {
    const broken: PendingDecision = { id: "p3", tool_name: "AskUserQuestion", tool_input: {} };
    render(<DecisionPrompt decision={broken} busy={false} onAnswer={vi.fn()} />);

    expect(screen.getByText(/answer it in the terminal/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send answer" })).not.toBeInTheDocument();
  });
});
