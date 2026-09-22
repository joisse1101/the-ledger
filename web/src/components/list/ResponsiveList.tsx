import { useViewportClass } from "../../hooks/useViewportClass";
import { ListCards } from "./ListCards";
import { ListTable } from "./ListTable";
import type { ResponsiveListProps } from "./types";

/** Picks the table or the card renderer by viewport width - only one is ever in the DOM, and
 *  both take the same rows, order and click handler, so switching never changes what is shown. */
export function ResponsiveList<T>(props: ResponsiveListProps<T>) {
  const viewport = useViewportClass();
  if (viewport === "narrow") return <ListCards {...props} />;
  return <ListTable {...props} showAllColumns={viewport === "wide"} />;
}
