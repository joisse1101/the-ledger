import { useSyncExternalStore } from "react";
import { MEDIUM_MIN, MEDIUM_UP_QUERY, WIDE_MIN, WIDE_UP_QUERY } from "../lib/breakpoints";

export type ViewportClass = "narrow" | "medium" | "wide";


export function classForWidth(width: number): ViewportClass {
  if (width >= WIDE_MIN) return "wide";
  if (width >= MEDIUM_MIN) return "medium";
  return "narrow";
}

function currentClass(): ViewportClass {
  if (window.matchMedia(WIDE_UP_QUERY).matches) return "wide";
  if (window.matchMedia(MEDIUM_UP_QUERY).matches) return "medium";
  return "narrow";
}

function subscribe(onChange: () => void): () => void {
  const queries = [window.matchMedia(MEDIUM_UP_QUERY), window.matchMedia(WIDE_UP_QUERY)];
  queries.forEach((query) => query.addEventListener("change", onChange));
  return () => queries.forEach((query) => query.removeEventListener("change", onChange));
}

/** Which width class the window is in, updating when it crosses a boundary (a phone
 *  rotating, a window resized) without remounting anything. It is for choosing which
 *  markup to render; everything that only needs to reflow is done in CSS. */
export function useViewportClass(): ViewportClass {
  return useSyncExternalStore(subscribe, currentClass, () => "wide");
}
