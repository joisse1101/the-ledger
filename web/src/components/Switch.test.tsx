import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { Switch } from "./Switch";

describe("Switch", () => {
  it("is a switch named by its label, off by default", () => {
    render(<Switch label="Auto-refresh" />);

    const toggle = screen.getByRole("switch", { name: "Auto-refresh" });
    expect(toggle).not.toBeChecked();
  });

  it("uncontrolled: flips on click and reports the new value", () => {
    const onChange = vi.fn();
    render(<Switch label="Auto-refresh" onChange={onChange} />);
    const toggle = screen.getByRole("switch");

    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
    expect(onChange).toHaveBeenLastCalledWith(true);

    fireEvent.click(toggle);
    expect(toggle).not.toBeChecked();
    expect(onChange).toHaveBeenLastCalledWith(false);
  });

  it("uncontrolled: starts from defaultChecked", () => {
    render(<Switch label="Auto-refresh" defaultChecked />);

    expect(screen.getByRole("switch")).toBeChecked();
  });

  it("controlled: only follows the checked prop, still reporting what the user asked for", () => {
    const onChange = vi.fn();
    const { rerender } = render(<Switch label="Remote mode" checked={false} onChange={onChange} />);
    const toggle = screen.getByRole("switch");

    fireEvent.click(toggle);
    expect(onChange).toHaveBeenCalledWith(true);
    expect(toggle).not.toBeChecked(); // parent hasn't accepted the change

    rerender(<Switch label="Remote mode" checked onChange={onChange} />);
    expect(toggle).toBeChecked();
  });

  it("controlled: a parent that stores the value drives it", () => {
    function Parent() {
      const [on, setOn] = useState(false);
      return <Switch label="Remote mode" checked={on} onChange={setOn} />;
    }
    render(<Parent />);
    const toggle = screen.getByRole("switch");

    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
    fireEvent.click(toggle);
    expect(toggle).not.toBeChecked();
  });

  it("disabled: renders the input disabled (browsers then refuse user clicks; jsdom's synthetic click ignores that, so it isn't clicked here)", () => {
    render(<Switch label="Remote mode" disabled defaultChecked />);
    const toggle = screen.getByRole("switch");

    expect(toggle).toBeDisabled();
    expect(toggle).toBeChecked(); // disabled doesn't change the value it shows
  });

  it("clicking the label text toggles it", () => {
    const onChange = vi.fn();
    render(<Switch label="Auto-refresh" onChange={onChange} />);

    fireEvent.click(screen.getByText("Auto-refresh"));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("works without a visible label when given an aria-label", () => {
    render(<Switch aria-label="Dark mode" />);

    expect(screen.getByRole("switch", { name: "Dark mode" })).toBeInTheDocument();
  });

  it("passes id and name through to the input", () => {
    render(<Switch label="Auto-refresh" id="auto" name="auto-refresh" />);

    const toggle = screen.getByRole("switch");
    expect(toggle).toHaveAttribute("id", "auto");
    expect(toggle).toHaveAttribute("name", "auto-refresh");
  });

  it("hides the decorative track from assistive tech", () => {
    const { container } = render(<Switch label="Auto-refresh" />);

    expect(container.querySelector("[aria-hidden='true']")).toBeInTheDocument();
  });

  it("applies the small size modifier only for size='sm'", () => {
    const { container, rerender } = render(<Switch label="A" size="sm" />);
    const rootClass = () => container.querySelector("label")!.className;
    const small = rootClass();

    rerender(<Switch label="A" />);
    expect(small).not.toBe(rootClass());
  });

  it("puts className on the outer label, keeping the component's own class, not on the input", () => {
    const { container } = render(<Switch label="A" className="toolbar-gap" />);

    expect(container.querySelector("label")).toHaveClass("toolbar-gap");
    expect(screen.getByRole("switch")).not.toHaveClass("toolbar-gap");
  });
});
