import { useSyncExternalStore } from "react";

export type ViewportClass = "narrow" | "medium" | "wide";

/** Class boundaries in CSS px: narrow < 640 <= medium < 1024 <= wide. */
export const MEDIUM_MIN = 640;
export const WIDE_MIN = 1024;

export function classForWidth(width: number): ViewportClass {
  if (width >= WIDE_MIN) return "wide";
  if (width >= MEDIUM_MIN) return "medium";
  return "narrow";
}

const mediumQuery = `(min-width: ${MEDIUM_MIN}px)`;
const wideQuery = `(min-width: ${WIDE_MIN}px)`;

function currentClass(): ViewportClass {
  if (window.matchMedia(wideQuery).matches) return "wide";
  if (window.matchMedia(mediumQuery).matches) return "medium";
  return "narrow";
}

function subscribe(onChange: () => void): () => void {
  const queries = [window.matchMedia(mediumQuery), window.matchMedia(wideQuery)];
  queries.forEach((query) => query.addEventListener("change", onChange));
  return () => queries.forEach((query) => query.removeEventListener("change", onChange));
}

/** Which width class the window is in, updating when it crosses a boundary (a phone
 *  rotating, a window resized) without remounting anything. It is for choosing which
 *  markup to render; everything that only needs to reflow is done in CSS. */
export function useViewportClass(): ViewportClass {
  return useSyncExternalStore(subscribe, currentClass, () => "wide");
}
