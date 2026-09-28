import { cardPriorityOf, type ResponsiveListProps } from "./types";
import { useClosingIds } from "./useClosingIds";

/** Card renderer for narrow screens: one button per item holding its primary fields plus small
 *  labelled chips for the secondary ones. Same rows, same order, same click handler as the table. */
export function ListCards<T>({
  columns,
  rows,
  rowId,
  onSelect,
  emptyMessage,
  ariaLabel,
  rowClassName,
  rowBadge,
  expandedIds,
  renderExpanded,
}: ResponsiveListProps<T>) {
  const { isClosing, onClosed } = useClosingIds(expandedIds);

  if (rows.length === 0) {
    return <p className="list-empty">{emptyMessage}</p>;
  }

  const primary = columns.filter((column) => cardPriorityOf(column) === "primary");
  const secondary = columns.filter((column) => cardPriorityOf(column) === "secondary");

  return (
    <ul className="list-cards" aria-label={ariaLabel}>
      {rows.map((row) => {
        const id = rowId(row);
        const expanded = expandedIds?.has(id) === true;
        return (
          <li key={id}>
            <button
              type="button"
              className={["list-card", rowClassName?.(row)].filter(Boolean).join(" ")}
              data-row-id={id}
              aria-expanded={renderExpanded ? expanded : undefined}
              onClick={() => onSelect(row)}
            >
              <div className="list-card-primary">
                {primary.map((column) => (
                  <span key={column.key} className="list-card-field">
                    {column.render(row)}
                  </span>
                ))}
                {rowBadge?.(row)}
              </div>
              {secondary.length > 0 && (
                <div className="list-card-secondary">
                  {secondary.map((column) => (
                    <span key={column.key} className="list-card-chip">
                      <span className="list-card-chip-label">{column.header}</span>
                      <span>{column.render(row)}</span>
                    </span>
                  ))}
                </div>
              )}
            </button>
            {(expanded || isClosing(id)) && renderExpanded && (
              <div
                className="list-card-expanded"
                data-collapsed={!expanded}
                onTransitionEnd={(event) => {
                  if (event.target === event.currentTarget && !expanded) onClosed(id);
                }}
              >
                <div className="list-expand-inner">{renderExpanded(row)}</div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
