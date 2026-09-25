/** The one place the app's width boundaries are defined, in CSS px:
 *  narrow < MEDIUM_MIN <= medium < WIDE_MIN <= wide.
 *  The stylesheets can't import this, so they name a boundary as `@media (--narrow)` and
 *  `build/mediaAliases.ts` swaps in the query built from `MEDIA_ALIASES` at build time. */
export const MEDIUM_MIN = 640;
export const WIDE_MIN = 1024;

/** Just under MEDIUM_MIN, so a `max-width` query and a `min-width: MEDIUM_MIN` one never both
 *  match (or both miss) at a fractional width such as a zoomed 639.5px window. */
const SUB_PIXEL_GAP = 0.02;

export const NARROW_QUERY = `(max-width: ${MEDIUM_MIN - SUB_PIXEL_GAP}px)`;
export const MEDIUM_UP_QUERY = `(min-width: ${MEDIUM_MIN}px)`;
export const WIDE_UP_QUERY = `(min-width: ${WIDE_MIN}px)`;

/** What each `@media (--name)` in the stylesheets stands for. */
export const MEDIA_ALIASES: Readonly<Record<string, string>> = {
  "--narrow": NARROW_QUERY,
  "--medium-up": MEDIUM_UP_QUERY,
  "--wide-up": WIDE_UP_QUERY,
};
