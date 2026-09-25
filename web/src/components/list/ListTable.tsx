import type { ResponsiveListProps } from "./types";

export interface ListTableProps<T> extends ResponsiveListProps<T> {
  /** Wide shows every column; medium (false) hides "low" priority ones. */
  showAllColumns: boolean;
}

/** Table renderer: sortable headers (when `sort` is given and a column has a `sortKey`), one row
 *  per item. The whole row is clickable for pointer users, but the row keeps its table semantics:
 *  keyboard and screen-reader users select it through a real button in its first visible cell. */
export function ListTable<T>({
  columns,
  rows,
  rowId,
  onSelect,
  emptyMessage,
  ariaLabel,
  sort,
  rowClassName,
  rowLabel,
  showAllColumns,
}: ListTableProps<T>) {
  const visible = columns.filter((column) => showAllColumns || column.priority === "high");

  if (rows.length === 0) {
    return <p className="list-empty">{emptyMessage}</p>;
  }

  return (
    <div className="list-table-scroll">
      <table className="list-table" aria-label={ariaLabel}>
        <thead>
          <tr>
            {visible.map((column) => (
              <th
                key={column.key}
                scope="col"
                data-align={column.align ?? "start"}
                aria-sort={
                  column.sortKey && sort
                    ? sort.field === column.sortKey
                      ? sort.dir === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                    : undefined
                }
              >
                {column.sortKey && sort ? (
                  <button type="button" className="sort-header" onClick={() => sort.onChange(column.sortKey!)}>
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
              <tr key={id} data-row-id={id} className={rowClassName?.(row)} onClick={() => onSelect(row)}>
                {visible.map((column, index) => (
                  <td key={column.key} data-align={column.align ?? "start"}>
                    {index === 0 ? (
                      <button
                        type="button"
                        className="row-select"
                        aria-label={rowLabel?.(row)}
                        onClick={(event) => {
                          // The row's own onClick would select a second time as this bubbles.
                          event.stopPropagation();
                          onSelect(row);
                        }}
                      >
                        {column.render(row)}
                      </button>
                    ) : (
                      column.render(row)
                    )}
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
