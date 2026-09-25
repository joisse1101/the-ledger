import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ListCards } from "./ListCards";
import { ListTable } from "./ListTable";
import type { ListColumn } from "./types";

interface Row {
  id: string;
  name: string;
  detail: string;
}

const rows: Row[] = [
  { id: "b", name: "Beta", detail: "second" },
  { id: "a", name: "Alpha", detail: "first" },
  { id: "c", name: "Gamma", detail: "third" },
];

const columns: ListColumn<Row>[] = [
  { key: "name", header: "Name", priority: "high", render: (r) => r.name },
  { key: "detail", header: "Detail", priority: "low", render: (r) => r.detail },
];

function rowIdsOf(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll("[data-row-id]")).map((el) => el.getAttribute("data-row-id")!);
}

describe("ListTable and ListCards", () => {
  it("render the same row IDs in the same order", () => {
    const noop = vi.fn();
    const { container: tableContainer } = render(
      <ListTable
        columns={columns}
        rows={rows}
        rowId={(r) => r.id}
        onSelect={noop}
        emptyMessage="none"
        ariaLabel="Rows"
        showAllColumns
      />,
    );
    const { container: cardContainer } = render(
      <ListCards columns={columns} rows={rows} rowId={(r) => r.id} onSelect={noop} emptyMessage="none" ariaLabel="Rows" />,
    );

    const expected = ["b", "a", "c"];
    expect(rowIdsOf(tableContainer)).toEqual(expected);
    expect(rowIdsOf(cardContainer)).toEqual(expected);
  });

  it("both call the select handler with the clicked row", () => {
    const onSelectTable = vi.fn();
    render(
      <ListTable
        columns={columns}
        rows={rows}
        rowId={(r) => r.id}
        onSelect={onSelectTable}
        emptyMessage="none"
        ariaLabel="Rows"
        showAllColumns
      />,
    );
    fireEvent.click(screen.getByText("Alpha"));
    expect(onSelectTable).toHaveBeenCalledWith(rows[1]);

    const onSelectCards = vi.fn();
    render(
      <ListCards columns={columns} rows={rows} rowId={(r) => r.id} onSelect={onSelectCards} emptyMessage="none" ariaLabel="Rows" />,
    );
    fireEvent.click(screen.getAllByText("Alpha")[1]);
    expect(onSelectCards).toHaveBeenCalledWith(rows[1]);
  });

  it("shows the empty message when there are no rows", () => {
    render(<ListTable columns={columns} rows={[]} rowId={(r) => r.id} onSelect={vi.fn()} emptyMessage="Nothing here" ariaLabel="Rows" showAllColumns />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("hides low-priority columns in the table when showAllColumns is false", () => {
    render(
      <ListTable columns={columns} rows={rows} rowId={(r) => r.id} onSelect={vi.fn()} emptyMessage="none" ariaLabel="Rows" showAllColumns={false} />,
    );
    expect(screen.queryByText("Detail")).not.toBeInTheDocument();
  });

  it("keeps real table rows, with one select button in each row's first cell", () => {
    render(
      <ListTable columns={columns} rows={rows} rowId={(r) => r.id} onSelect={vi.fn()} emptyMessage="none" ariaLabel="Rows" showAllColumns />,
    );
    // Header row + one per item; none of them is flattened into a button.
    expect(screen.getAllByRole("row")).toHaveLength(rows.length + 1);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(rows.length);
    for (const [index, button] of buttons.entries()) {
      expect(button.tagName).toBe("BUTTON");
      expect(button).toHaveAttribute("type", "button");
      expect(button).toHaveTextContent(rows[index].name);
      expect(button.closest("td")).toBe(button.closest("tr")!.querySelector("td"));
    }
  });

  it("selects exactly once whether the button or another part of the row is clicked", () => {
    const onSelect = vi.fn();
    render(
      <ListTable columns={columns} rows={rows} rowId={(r) => r.id} onSelect={onSelect} emptyMessage="none" ariaLabel="Rows" showAllColumns />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenLastCalledWith(rows[1]);

    fireEvent.click(screen.getByText("third"));
    expect(onSelect).toHaveBeenCalledTimes(2);
    expect(onSelect).toHaveBeenLastCalledWith(rows[2]);
  });

  it("names the row button from rowLabel when one is supplied", () => {
    const onSelect = vi.fn();
    render(
      <ListTable
        columns={columns}
        rows={rows}
        rowId={(r) => r.id}
        onSelect={onSelect}
        emptyMessage="none"
        ariaLabel="Rows"
        showAllColumns
        rowLabel={(r) => `Open ${r.name}`}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Open Alpha" }));
    expect(onSelect).toHaveBeenCalledWith(rows[1]);
  });

  it("puts aria-sort on the sortable column headers, not on their buttons", () => {
    const sortable: ListColumn<Row>[] = [
      { ...columns[0], sortKey: "name" },
      { ...columns[1], sortKey: "detail" },
      { key: "plain", header: "Plain", priority: "high", render: () => "x" },
    ];
    render(
      <ListTable
        columns={sortable}
        rows={rows}
        rowId={(r) => r.id}
        onSelect={vi.fn()}
        emptyMessage="none"
        ariaLabel="Rows"
        showAllColumns
        sort={{ field: "name", dir: "desc", onChange: vi.fn() }}
      />,
    );
    expect(screen.getByRole("columnheader", { name: /Name/ })).toHaveAttribute("aria-sort", "descending");
    expect(screen.getByRole("columnheader", { name: /Detail/ })).toHaveAttribute("aria-sort", "none");
    expect(screen.getByRole("columnheader", { name: "Plain" })).not.toHaveAttribute("aria-sort");
    expect(screen.getByRole("button", { name: /Name/ })).not.toHaveAttribute("aria-sort");
  });

  it("drops a column marked cardPriority hidden from the card", () => {
    const hiddenColumns: ListColumn<Row>[] = [
      columns[0],
      { ...columns[1], cardPriority: "hidden" },
    ];
    render(<ListCards columns={hiddenColumns} rows={rows} rowId={(r) => r.id} onSelect={vi.fn()} emptyMessage="none" ariaLabel="Rows" />);
    expect(screen.queryByText("Detail")).not.toBeInTheDocument();
  });
});
