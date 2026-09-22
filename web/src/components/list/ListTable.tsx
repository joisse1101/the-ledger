import type { KeyboardEvent } from "react";
import type { ResponsiveListProps } from "./types";

export interface ListTableProps<T> extends ResponsiveListProps<T> {
  /** Wide shows every column; medium (false) hides "low" priority ones. */
  showAllColumns: boolean;
}

/** Table renderer: sortable headers (when `sort` is given and a column has a `sortKey`), one row
 *  per item, the whole row clickable and keyboard-activatable. */
export function ListTable<T>({
  columns,
  rows,
  rowId,
  onSelect,
  emptyMessage,
  ariaLabel,
  sort,
  rowClassName,
  showAllColumns,
}: ListTableProps<T>) {
  const visible = columns.filter((column) => showAllColumns || column.priority === "high");

  if (rows.length === 0) {
    return <p className="list-empty">{emptyMessage}</p>;
  }

  const activate = (row: T) => (event: KeyboardEvent<HTMLTableRowElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(row);
    }
  };

  return (
    <div className="list-table-scroll">
      <table className="list-table" aria-label={ariaLabel}>
        <thead>
          <tr>
            {visible.map((column) => (
              <th key={column.key} scope="col" data-align={column.align ?? "start"}>
                {column.sortKey && sort ? (
                  <button
                    type="button"
                    className="sort-header"
                    onClick={() => sort.onChange(column.sortKey!)}
                    aria-sort={sort.field === column.sortKey ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                  >
                    {column.header}
                    {sort.field === column.sortKey && (
                      <span aria-hidden="true">{sort.dir === "asc" ? " ▲" : " ▼"}</span>
                    )}
                  </button>
                ) : (
                  column.header
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const id = rowId(row);
            return (
              <tr
                key={id}
                data-row-id={id}
                tabIndex={0}
                role="button"
                className={rowClassName?.(row)}
                onClick={() => onSelect(row)}
                onKeyDown={activate(row)}
              >
                {visible.map((column) => (
                  <td key={column.key} data-align={column.align ?? "start"}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
