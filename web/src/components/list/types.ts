import type { ReactNode } from "react";

/** Wide tables show every column; medium tables show only "high" priority ones. */
export type ColumnPriority = "high" | "low";

/** Where a column appears on a narrow-screen card. Defaults from `priority` when omitted:
 *  "high" -> "primary" (shown as one of the card's headline fields), "low" -> "secondary"
 *  (shown as a small labelled chip). "hidden" drops it from the card entirely - it is still
 *  reachable by opening the item's detail view. */
export type CardPriority = "primary" | "secondary" | "hidden";

export interface ListColumn<T> {
  key: string;
  header: string;
  priority: ColumnPriority;
  cardPriority?: CardPriority;
  align?: "start" | "end";
  /** Present and truthy enables a clickable, sortable header for this column. */
  sortKey?: string;
  render: (row: T) => ReactNode;
}

export interface ResponsiveListSort {
  field: string;
  dir: "asc" | "desc";
  onChange: (field: string) => void;
}

export interface ResponsiveListProps<T> {
  columns: ListColumn<T>[];
  rows: T[];
  rowId: (row: T) => string;
  onSelect: (row: T) => void;
  emptyMessage: ReactNode;
  ariaLabel: string;
  sort?: ResponsiveListSort;
  /** Extra class on a row/card, e.g. to accent a live session. */
  rowClassName?: (row: T) => string | undefined;
  /** Rendered alongside the card's primary fields, e.g. a "Live" badge. */
  rowBadge?: (row: T) => ReactNode;
  /** Accessible name for the table row's select button, when the first cell's own text doesn't
   *  say what selecting does (e.g. "Select project X to delete"). Table only: a card's button
   *  already names itself from all its fields, which a label here would replace. */
  rowLabel?: (row: T) => string;
}

export function cardPriorityOf<T>(column: ListColumn<T>): CardPriority {
  return column.cardPriority ?? (column.priority === "high" ? "primary" : "secondary");
}
