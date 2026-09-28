import { act, fireEvent, render, screen } from "@testing-library/react";
import { StrictMode } from "react";
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

  it("shows renderExpanded content for every id in expandedIds at once, marking those rows aria-expanded", () => {
    render(
      <ListTable
        columns={columns}
        rows={rows}
        rowId={(r) => r.id}
        onSelect={vi.fn()}
        emptyMessage="none"
        ariaLabel="Rows"
        showAllColumns
        expandedIds={new Set(["b", "c"])}
        renderExpanded={(r) => <div>Expanded: {r.name}</div>}
      />,
    );
    expect(screen.getByText("Expanded: Beta")).toBeInTheDocument();
    expect(screen.getByText("Expanded: Gamma")).toBeInTheDocument();
    expect(screen.queryByText("Expanded: Alpha")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Beta" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Alpha" })).toHaveAttribute("aria-expanded", "false");
  });

  it("shows renderExpanded content beneath a card, outside the card's own button", () => {
    render(
      <ListCards
        columns={columns}
        rows={rows}
        rowId={(r) => r.id}
        onSelect={vi.fn()}
        emptyMessage="none"
        ariaLabel="Rows"
        expandedIds={new Set(["a"])}
        renderExpanded={(r) => <div data-testid={`expanded-${r.id}`}>Expanded: {r.name}</div>}
      />,
    );
    const expanded = screen.getByTestId("expanded-a");
    const button = screen.getByRole("button", { name: /Alpha/ });
    expect(expanded).toBeInTheDocument();
    expect(button).not.toContainElement(expanded);
    expect(button).toHaveAttribute("aria-expanded", "true");
  });

  it("renders no aria-expanded attribute when renderExpanded is not supplied", () => {
    render(
      <ListTable columns={columns} rows={rows} rowId={(r) => r.id} onSelect={vi.fn()} emptyMessage="none" ariaLabel="Rows" showAllColumns />,
    );
    expect(screen.getByRole("button", { name: "Alpha" })).not.toHaveAttribute("aria-expanded");
  });

  describe("closing a row/card's expanded panel", () => {
    function tableExpandedElement(expandedIds: string[]) {
      return (
        <ListTable
          columns={columns}
          rows={rows}
          rowId={(r) => r.id}
          onSelect={vi.fn()}
          emptyMessage="none"
          ariaLabel="Rows"
          showAllColumns
          expandedIds={new Set(expandedIds)}
          renderExpanded={(r) => <div>Expanded: {r.name}</div>}
        />
      );
    }

    function renderTableExpanded(expandedIds: string[]) {
      return render(tableExpandedElement(expandedIds));
    }

    it("keeps a table row's panel mounted, marked collapsed, until its transition ends", () => {
      const { rerender } = renderTableExpanded(["b"]);
      rerender(
        <ListTable
          columns={columns}
          rows={rows}
          rowId={(r) => r.id}
          onSelect={vi.fn()}
          emptyMessage="none"
          ariaLabel="Rows"
          showAllColumns
          expandedIds={new Set()}
          renderExpanded={(r) => <div>Expanded: {r.name}</div>}
        />,
      );

      // Still there, right after the row itself stopped being expanded.
      expect(screen.getByText("Expanded: Beta")).toBeInTheDocument();
      const panel = document.querySelector(".list-expand")!;
      expect(panel).toHaveAttribute("data-collapsed", "true");

      fireEvent.transitionEnd(panel);
      expect(screen.queryByText("Expanded: Beta")).not.toBeInTheDocument();
    });

    it("cancels a still-closing row's removal if it's expanded again first", () => {
      const { rerender } = renderTableExpanded(["b"]);
      rerender(
        <ListTable
          columns={columns}
          rows={rows}
          rowId={(r) => r.id}
          onSelect={vi.fn()}
          emptyMessage="none"
          ariaLabel="Rows"
          showAllColumns
          expandedIds={new Set()}
          renderExpanded={(r) => <div>Expanded: {r.name}</div>}
        />,
      );
      rerender(
        <ListTable
          columns={columns}
          rows={rows}
          rowId={(r) => r.id}
          onSelect={vi.fn()}
          emptyMessage="none"
          ariaLabel="Rows"
          showAllColumns
          expandedIds={new Set(["b"])}
          renderExpanded={(r) => <div>Expanded: {r.name}</div>}
        />,
      );

      expect(screen.getByText("Expanded: Beta")).toBeInTheDocument();
      expect(document.querySelector(".list-expand")).toHaveAttribute("data-collapsed", "false");
    });

    it("removes a card's panel once its transition ends", () => {
      const { rerender } = render(
        <ListCards
          columns={columns}
          rows={rows}
          rowId={(r) => r.id}
          onSelect={vi.fn()}
          emptyMessage="none"
          ariaLabel="Rows"
          expandedIds={new Set(["a"])}
          renderExpanded={(r) => <div>Expanded: {r.name}</div>}
        />,
      );
      rerender(
        <ListCards
          columns={columns}
          rows={rows}
          rowId={(r) => r.id}
          onSelect={vi.fn()}
          emptyMessage="none"
          ariaLabel="Rows"
          expandedIds={new Set()}
          renderExpanded={(r) => <div>Expanded: {r.name}</div>}
        />,
      );

      expect(screen.getByText("Expanded: Alpha")).toBeInTheDocument();
      const panel = document.querySelector(".list-card-expanded")!;
      expect(panel).toHaveAttribute("data-collapsed", "true");

      fireEvent.transitionEnd(panel);
      expect(screen.queryByText("Expanded: Alpha")).not.toBeInTheDocument();
    });

    it("removes the panel via a fallback timer, but not before the CSS transition (0.75s) could finish", () => {
      // Regression test: the fallback timer used to fire at 300ms, well inside the 0.75s CSS
      // transition, cutting the animation off partway - visually indistinguishable from no
      // animation ever having played.
      vi.useFakeTimers();
      try {
        const { rerender } = renderTableExpanded(["b"]);
        rerender(
          <ListTable
            columns={columns}
            rows={rows}
            rowId={(r) => r.id}
            onSelect={vi.fn()}
            emptyMessage="none"
            ariaLabel="Rows"
            showAllColumns
            expandedIds={new Set()}
            renderExpanded={(r) => <div>Expanded: {r.name}</div>}
          />,
        );

        expect(screen.getByText("Expanded: Beta")).toBeInTheDocument();
        act(() => {
          vi.advanceTimersByTime(750);
        });
        expect(screen.getByText("Expanded: Beta")).toBeInTheDocument();

        act(() => {
          vi.advanceTimersByTime(250);
        });
        expect(screen.queryByText("Expanded: Beta")).not.toBeInTheDocument();
      } finally {
        vi.useRealTimers();
      }
    });

    it("still animates closed under StrictMode's double-invoked renders", () => {
      // Regression test: an earlier version tracked "was this row just closed?" with a ref
      // mutated inline during render. StrictMode calls the render function twice per commit with
      // the same props/state; the ref's mutation from the first (discarded) call was already in
      // place by the second (real) one, so the row's "closing" branch never ran and the panel was
      // yanked out immediately instead of staying mounted to animate shut.
      const { rerender } = render(<StrictMode>{tableExpandedElement(["b"])}</StrictMode>);
      rerender(<StrictMode>{tableExpandedElement([])}</StrictMode>);

      expect(screen.getByText("Expanded: Beta")).toBeInTheDocument();
      expect(document.querySelector(".list-expand")).toHaveAttribute("data-collapsed", "true");
    });
  });
});
