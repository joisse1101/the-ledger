import { useEffect, useState } from "react";

const EMPTY = new Set<string>();
// A safety net for onTransitionEnd never firing at all (prefers-reduced-motion sets
// transition: none there, so no property ever transitions) - not the primary removal path, so it
// must stay comfortably longer than the CSS transition duration itself (.list-expand/
// .list-card-expanded in sessions.css, currently 0.75s): firing sooner would cut that transition
// off mid-animation and yank the panel out from under it, which looks identical to no animation
// having played at all.
const CLOSE_TIMEOUT_MS = 1000;

function sameMembers(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const id of a) if (!b.has(id)) return false;
  return true;
}

/** Tracks ids that just dropped out of `expandedIds`, so a renderer can keep rendering (and
 *  CSS-transitioning closed) a row's expanded panel for one more moment instead of yanking it out
 *  of the DOM the instant it collapses. Call `onClosed(id)` from that transition's `onTransitionEnd`
 *  to actually stop rendering it early; an effect-scheduled timer backs that up regardless, so an
 *  instant or skipped transition (reduced motion) can't leave an id stuck "closing" forever.
 *  Re-expanding an id before it's done closing drops it immediately, so reopening never fights the
 *  same element's own animation.
 *
 *  Diffs during render (via `useState`, never a ref) rather than in an effect - an effect runs one
 *  render after `expandedIds` drops an id, by which point the row asking "am I closing?" has
 *  already been skipped and unmounted with no transition to play at all. It has to be state and
 *  not a ref: StrictMode double-invokes render with the same props/state both times, so a ref
 *  mutated inline here would already reflect the "new" value by the second call, silently skipping
 *  this whole branch - state reads stay consistent across both calls instead. */
export function useClosingIds(expandedIds: Set<string> | undefined) {
  const current = expandedIds ?? EMPTY;
  const [previous, setPrevious] = useState(current);
  const [closing, setClosing] = useState<Set<string>>(EMPTY);

  if (previous !== current) {
    setPrevious(current);
    setClosing((prev) => {
      const next = new Set(prev);
      for (const id of previous) {
        if (!current.has(id)) next.add(id);
      }
      for (const id of current) next.delete(id); // reopened before it finished closing
      return sameMembers(next, prev) ? prev : next;
    });
  }

  const onClosed = (id: string) => {
    setClosing((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  useEffect(() => {
    if (closing.size === 0) return;
    const timers = [...closing].map((id) => setTimeout(() => onClosed(id), CLOSE_TIMEOUT_MS));
    return () => {
      for (const timer of timers) clearTimeout(timer);
    };
    // onClosed is a fresh function each render but stable in behavior; only closing membership
    // should reschedule these timers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [closing]);

  return { isClosing: (id: string) => closing.has(id), onClosed };
}
