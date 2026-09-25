/** The browser's default root font size, which the stylesheets' rem values are written against. */
const DEFAULT_ROOT_PX = 16;

/** Chart sizes are rounded to this many steps per pixel, so specs don't carry float noise. */
const ROUNDING_STEPS_PER_PX = 10;

/** Turns a size in default-root px into one for the current UI size. */
export type Scaled = (px: number) => number;

/** The UI's current size relative to the default root (1 on a phone, smaller on desktop — see the
 *  `html` font-size in styles/app.css). CSS follows it through rem; chart specs are plain numbers
 *  Vega draws in px, so they go through a `Scaled` to stay in step with the page. */
export function uiScale(): number {
  const rootPx = parseFloat(getComputedStyle(document.documentElement).fontSize);
  return Number.isFinite(rootPx) && rootPx > 0 ? rootPx / DEFAULT_ROOT_PX : 1;
}

export function scaledBy(scale: number): Scaled {
  return (px) => Math.round(px * scale * ROUNDING_STEPS_PER_PX) / ROUNDING_STEPS_PER_PX;
}
