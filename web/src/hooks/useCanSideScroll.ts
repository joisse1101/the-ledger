import { useLayoutEffect, useState, type RefObject } from "react";

/** Sub-pixel rounding on high-DPI screens can leave a scroller a fraction short of either edge. */
const EDGE_TOLERANCE_PX = 2;

/** Whether the element has more content hidden past its left / right edge, kept current as it
 *  scrolls, resizes, or gains/loses children. Drives the fade cues on a horizontally-scrolling
 *  strip so a clipped option looks scrollable instead of cut off. */
export function useCanSideScroll(ref: RefObject<HTMLElement | null>) {
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const check = () => {
      const overflowing = el.scrollWidth > el.clientWidth;
      setCanScrollLeft(overflowing && el.scrollLeft > EDGE_TOLERANCE_PX);
      setCanScrollRight(
        overflowing && Math.ceil(el.scrollLeft + el.clientWidth) < el.scrollWidth - EDGE_TOLERANCE_PX,
      );
    };

    // The scroller's own box doesn't change when its content grows, so its children are observed
    // too; the MutationObserver keeps that set current when children come and go.
    const resizeObserver = new ResizeObserver(check);
    const observeChildren = () => {
      resizeObserver.disconnect();
      resizeObserver.observe(el);
      Array.from(el.children).forEach((child) => resizeObserver.observe(child));
      check();
    };
    const mutationObserver = new MutationObserver(observeChildren);
    mutationObserver.observe(el, { childList: true });

    observeChildren();
    el.addEventListener("scroll", check, { passive: true });

    return () => {
      resizeObserver.disconnect();
      mutationObserver.disconnect();
      el.removeEventListener("scroll", check);
    };
  }, [ref]);

  return { canScrollLeft, canScrollRight };
}
