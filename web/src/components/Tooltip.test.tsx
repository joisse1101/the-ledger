import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Tooltip } from "./Tooltip";

describe("Tooltip", () => {
  it("renders a closed trigger button and the tooltip text", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);

    expect(screen.getByRole("button", { name: "About Auto-refresh" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("tooltip")).toHaveTextContent("Refreshes every 2s");
  });

  it("names the trigger generically without a label", () => {
    render(<Tooltip tooltip="Some help" />);

    expect(screen.getByRole("button", { name: "More information" })).toBeInTheDocument();
  });

  it("describes the trigger by the tooltip text", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);

    expect(screen.getByRole("button")).toHaveAccessibleDescription("Refreshes every 2s");
  });

  it("tapping the trigger opens it, and tapping again closes it", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("Escape closes it", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("other keys leave it open", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    fireEvent.keyDown(trigger, { key: "a" });
    expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  it("tapping elsewhere closes it", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    fireEvent.pointerDown(document.body);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("tapping inside it (on the bubble) doesn't close it", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    fireEvent.pointerDown(screen.getByRole("tooltip"));
    expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  it("the mouse moving away closes it", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    fireEvent.mouseLeave(trigger.parentElement!);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("dragging a finger on the page closes it", () => {
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    fireEvent.touchMove(document.body);
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("dragging inside a nested scroll container closes it too", () => {
    render(
      <div data-testid="scroller">
        <Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />
      </div>,
    );
    const trigger = screen.getByRole("button");

    fireEvent.click(trigger);
    fireEvent.touchMove(screen.getByTestId("scroller"));
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("removes its window/document listeners once closed and on unmount", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);

    fireEvent.click(screen.getByRole("button"));
    expect(addSpy.mock.calls.filter(([type]) => type === "touchmove")).toHaveLength(1);

    unmount();
    expect(removeSpy.mock.calls.filter(([type]) => type === "touchmove")).toHaveLength(1);
    // Nothing left to throw or warn about a state update on an unmounted component.
    expect(() => {
      fireEvent.pointerDown(document.body);
      fireEvent.touchMove(document.body);
    }).not.toThrow();

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it("doesn't listen for touch moves while closed", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    render(<Tooltip label="Auto-refresh" tooltip="Refreshes every 2s" />);

    expect(addSpy.mock.calls.filter(([type]) => type === "touchmove")).toHaveLength(0);
    addSpy.mockRestore();
  });

  it("gives each tooltip its own id so several can share a page", () => {
    render(
      <>
        <Tooltip label="A" tooltip="First" />
        <Tooltip label="B" tooltip="Second" />
      </>,
    );

    const [a, b] = screen.getAllByRole("button");
    expect(a).toHaveAccessibleDescription("First");
    expect(b).toHaveAccessibleDescription("Second");
  });
});
