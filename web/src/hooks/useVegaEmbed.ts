import { useEffect, type RefObject } from "react";
import type { Result } from "vega-embed";

/** Lazily imports `vega-embed` and embeds `spec` into `containerRef`, finalizing the previous
 *  view before re-embedding whenever `spec` changes (new data, or a rebuilt spec after a theme
 *  change) and on unmount. `null` renders nothing. */
export function useVegaEmbed(containerRef: RefObject<HTMLDivElement | null>, spec: object | null): void {
  useEffect(() => {
    if (!spec) return;
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    let result: Result | null = null;

    import("vega-embed").then(({ default: vegaEmbed }) => {
      if (cancelled) return;
      vegaEmbed(container, spec as never, { actions: false, renderer: "svg" }).then((embedded) => {
        if (cancelled) {
          embedded.finalize();
          return;
        }
        result = embedded;
      });
    });

    return () => {
      cancelled = true;
      result?.finalize();
    };
  }, [containerRef, spec]);
}
