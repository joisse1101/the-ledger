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

  it("drops a column marked cardPriority hidden from the card", () => {
    const hiddenColumns: ListColumn<Row>[] = [
      columns[0],
      { ...columns[1], cardPriority: "hidden" },
    ];
    render(<ListCards columns={hiddenColumns} rows={rows} rowId={(r) => r.id} onSelect={vi.fn()} emptyMessage="none" ariaLabel="Rows" />);
    expect(screen.queryByText("Detail")).not.toBeInTheDocument();
  });
});
