import { useMemo, useSyncExternalStore } from "react";
import { scaledBy, uiScale, type Scaled } from "../lib/uiScale";

function subscribe(onChange: () => void): () => void {
  // The root font size changes with the window width (and browser zoom), and both fire `resize`.
  // The snapshot is a number, so React only re-renders when the scale actually changes.
  window.addEventListener("resize", onChange);
  return () => window.removeEventListener("resize", onChange);
}

/** A `Scaled` for the current UI size, replaced whenever that size changes. For values that
 *  can't use rem (chart specs) — put it in the dependency list of whatever builds them. */
export function useScaled(): Scaled {
  const scale = useSyncExternalStore(subscribe, uiScale, () => 1);
  return useMemo(() => scaledBy(scale), [scale]);
}
