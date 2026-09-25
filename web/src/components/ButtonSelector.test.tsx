import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ButtonSelector } from "./ButtonSelector";

const OPTIONS = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
  { value: "c", label: "Gamma" },
];

describe("ButtonSelector (single-select)", () => {
  it("is a radio group named by its visible label, with the value's option checked", () => {
    render(<ButtonSelector label="Letter" options={OPTIONS} value="b" onChange={() => {}} />);

    const group = screen.getByRole("radiogroup", { name: "Letter" });
    expect(group).toBeInTheDocument();
    expect(screen.getByText("Letter")).toBeVisible();
    expect(screen.getByRole("radio", { name: "Beta" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "Alpha" })).toHaveAttribute("aria-checked", "false");
  });

  it("reports the clicked option, and stays on the prop until it changes", () => {
    const onChange = vi.fn();
    render(<ButtonSelector label="Letter" options={OPTIONS} value="a" onChange={onChange} />);

    fireEvent.click(screen.getByRole("radio", { name: "Gamma" }));

    expect(onChange).toHaveBeenCalledExactlyOnceWith("c");
    expect(screen.getByRole("radio", { name: "Alpha" })).toHaveAttribute("aria-checked", "true");
  });

  it("doesn't report a click on the option that's already selected", () => {
    const onChange = vi.fn();
    render(<ButtonSelector label="Letter" options={OPTIONS} value="a" onChange={onChange} />);

    fireEvent.click(screen.getByRole("radio", { name: "Alpha" }));

    expect(onChange).not.toHaveBeenCalled();
  });

  it("works with numeric values", () => {
    const onChange = vi.fn();
    render(
      <ButtonSelector
        label="Count"
        options={[
          { value: 1, label: "One" },
          { value: 2, label: "Two" },
        ]}
        value={1}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("radio", { name: "Two" }));

    expect(onChange).toHaveBeenCalledWith(2);
  });

  it("hideLabel keeps the group named for assistive tech without rendering the text", () => {
    render(<ButtonSelector label="Letter" hideLabel options={OPTIONS} value="a" onChange={() => {}} />);

    expect(screen.getByRole("radiogroup", { name: "Letter" })).toBeInTheDocument();
    expect(screen.queryByText("Letter")).not.toBeInTheDocument();
  });

  it("gives two selectors on one page separate names", () => {
    render(
      <>
        <ButtonSelector label="First" options={OPTIONS} value="a" onChange={() => {}} />
        <ButtonSelector label="Second" options={OPTIONS} value="b" onChange={() => {}} />
      </>,
    );

    expect(screen.getByRole("radiogroup", { name: "First" })).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: "Second" })).toBeInTheDocument();
  });
});

describe("ButtonSelector (multi-select)", () => {
  function Harness({ initial = [] as string[] }) {
    const [value, setValue] = useState(initial);
    return <ButtonSelector multiple label="Letters" options={OPTIONS} value={value} onChange={setValue} />;
  }

  it("is a group of toggle buttons reflecting each option's state", () => {
    render(<Harness initial={["a", "c"]} />);

    expect(screen.getByRole("group", { name: "Letters" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alpha" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Beta" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Gamma" })).toHaveAttribute("aria-pressed", "true");
  });

  it("toggles options independently, in click order", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <ButtonSelector multiple label="Letters" options={OPTIONS} value={["a"]} onChange={onChange} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Gamma" }));
    expect(onChange).toHaveBeenLastCalledWith(["a", "c"]);

    rerender(<ButtonSelector multiple label="Letters" options={OPTIONS} value={["a", "c"]} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    expect(onChange).toHaveBeenLastCalledWith(["c"]);
  });

  it("can be emptied", () => {
    render(<Harness initial={["b"]} />);

    fireEvent.click(screen.getByRole("button", { name: "Beta" }));

    expect(screen.getByRole("button", { name: "Beta" })).toHaveAttribute("aria-pressed", "false");
  });
});

describe("ButtonSelector scroll cues", () => {
  const originals = {
    scrollWidth: Object.getOwnPropertyDescriptor(Element.prototype, "scrollWidth"),
    clientWidth: Object.getOwnPropertyDescriptor(Element.prototype, "clientWidth"),
  };

  afterEach(() => {
    for (const [key, descriptor] of Object.entries(originals)) {
      if (descriptor) Object.defineProperty(Element.prototype, key, descriptor);
    }
  });

  function layout(scrollWidth: number, clientWidth: number) {
    Object.defineProperty(Element.prototype, "scrollWidth", { configurable: true, get: () => scrollWidth });
    Object.defineProperty(Element.prototype, "clientWidth", { configurable: true, get: () => clientWidth });
  }

  const group = () => screen.getByRole("radiogroup");
  const renderSelector = () =>
    render(<ButtonSelector label="Letter" options={OPTIONS} value="a" onChange={() => {}} />);

  it("shows no fade when everything fits", () => {
    layout(200, 200);
    renderSelector();

    expect(group()).not.toHaveAttribute("data-fade-start");
    expect(group()).not.toHaveAttribute("data-fade-end");
  });

  it("fades only the far edge at the start of an overflowing row", () => {
    layout(500, 200);
    renderSelector();

    expect(group()).not.toHaveAttribute("data-fade-start");
    expect(group()).toHaveAttribute("data-fade-end");
  });

  it("fades both edges mid-scroll, then only the near edge at the end", () => {
    layout(500, 200);
    renderSelector();

    act(() => {
      group().scrollLeft = 100;
      group().dispatchEvent(new Event("scroll"));
    });
    expect(group()).toHaveAttribute("data-fade-start");
    expect(group()).toHaveAttribute("data-fade-end");

    act(() => {
      group().scrollLeft = 300;
      group().dispatchEvent(new Event("scroll"));
    });
    expect(group()).toHaveAttribute("data-fade-start");
    expect(group()).not.toHaveAttribute("data-fade-end");
  });
});
