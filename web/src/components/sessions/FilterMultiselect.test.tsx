import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { FilterMultiselect } from "./FilterMultiselect";

const detailsOf = (label: string) =>
  screen.getByText(label, { selector: "summary" }).closest("details") as HTMLDetailsElement;

describe("FilterMultiselect", () => {
  it("lists every option as a checkbox, checked when selected", () => {
    render(<FilterMultiselect label="Project" options={["a", "b", "c"]} selected={["b"]} onChange={() => {}} />);

    expect(screen.getAllByRole("checkbox")).toHaveLength(3);
    expect(screen.getByRole("checkbox", { name: "a" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "b" })).toBeChecked();
  });

  it("shows the selected count only when something is selected", () => {
    const { rerender } = render(<FilterMultiselect label="Project" options={["a", "b"]} selected={[]} onChange={() => {}} />);
    expect(document.querySelector(".filter-multiselect-count")).not.toBeInTheDocument();

    rerender(<FilterMultiselect label="Project" options={["a", "b"]} selected={["a", "b"]} onChange={() => {}} />);
    expect(document.querySelector(".filter-multiselect-count")).toHaveTextContent("2");
  });

  it("says there are no values yet when there are no options", () => {
    render(<FilterMultiselect label="Branch" options={[]} selected={[]} onChange={() => {}} />);

    expect(screen.getByText("No values yet")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("adds an unselected option and removes a selected one, without mutating the prop", () => {
    const selected = ["b"];
    const onChange = vi.fn();
    render(<FilterMultiselect label="Project" options={["a", "b"]} selected={selected} onChange={onChange} />);

    fireEvent.click(screen.getByRole("checkbox", { name: "a" }));
    expect(onChange).toHaveBeenLastCalledWith(["b", "a"]);

    fireEvent.click(screen.getByRole("checkbox", { name: "b" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
    expect(selected).toEqual(["b"]);
  });

  it("a parent that stores the selection drives the checkboxes", () => {
    function Parent() {
      const [selected, setSelected] = useState<string[]>([]);
      return <FilterMultiselect label="Project" options={["a", "b"]} selected={selected} onChange={setSelected} />;
    }
    render(<Parent />);

    fireEvent.click(screen.getByRole("checkbox", { name: "a" }));
    expect(screen.getByRole("checkbox", { name: "a" })).toBeChecked();
    fireEvent.click(screen.getByRole("checkbox", { name: "a" }));
    expect(screen.getByRole("checkbox", { name: "a" })).not.toBeChecked();
  });

  describe("closing on outside click", () => {
    it("closes an open list when clicking elsewhere on the page", () => {
      render(
        <div>
          <FilterMultiselect label="Project" options={["a"]} selected={[]} onChange={() => {}} />
          <button>elsewhere</button>
        </div>,
      );
      const details = detailsOf("Project");
      details.open = true;

      fireEvent.click(screen.getByRole("button", { name: "elsewhere" }));

      expect(details.open).toBe(false);
    });

    it("stays open when clicking inside it, including ticking a checkbox", () => {
      render(<FilterMultiselect label="Project" options={["a"]} selected={[]} onChange={() => {}} />);
      const details = detailsOf("Project");
      details.open = true;

      fireEvent.click(screen.getByRole("checkbox", { name: "a" }));
      fireEvent.click(screen.getByText("a"));

      expect(details.open).toBe(true);
    });

    it("opening one filter closes another, and each only closes itself", () => {
      render(
        <div>
          <FilterMultiselect label="Project" options={["a"]} selected={[]} onChange={() => {}} />
          <FilterMultiselect label="Branch" options={["main"]} selected={[]} onChange={() => {}} />
        </div>,
      );
      const project = detailsOf("Project");
      const branch = detailsOf("Branch");
      project.open = true;

      // Clicking Branch's summary opens Branch natively and is outside Project, so Project closes.
      fireEvent.click(screen.getByText("Branch", { selector: "summary" }));

      expect(project.open).toBe(false);
      expect(branch.open).toBe(true);
    });

    it("works for labels with spaces or duplicated labels (no id/selector lookup)", () => {
      const { container } = render(
        <div>
          <FilterMultiselect label="Git branch" options={["a"]} selected={[]} onChange={() => {}} />
          <FilterMultiselect label="Git branch" options={["b"]} selected={[]} onChange={() => {}} />
          <button>elsewhere</button>
        </div>,
      );
      const all = Array.from(container.querySelectorAll("details"));
      all.forEach((d) => (d.open = true));

      fireEvent.click(screen.getByRole("button", { name: "elsewhere" }));

      expect(all.map((d) => d.open)).toEqual([false, false]);
    });

    it("stops listening once unmounted", () => {
      const remove = vi.spyOn(document, "removeEventListener");
      const { unmount } = render(<FilterMultiselect label="Project" options={["a"]} selected={[]} onChange={() => {}} />);

      unmount();

      expect(remove).toHaveBeenCalledWith("click", expect.any(Function));
      remove.mockRestore();
    });
  });
});
