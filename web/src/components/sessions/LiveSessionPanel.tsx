import { useEffect, useRef } from "react";
import { useLive, useMeta } from "../../api/queries";
import { MEDIUM_MIN } from "../../hooks/useViewportClass";
import { CloseIcon } from "../icons";
import { LiveControl } from "./LiveControl";

/** Same boundary as `useViewportClass`'s "narrow" (under `MEDIUM_MIN`). */
const NARROW_QUERY = `(max-width: ${MEDIUM_MIN - 0.02}px)`;

const isNarrow = () => window.matchMedia(NARROW_QUERY).matches;

export interface LiveSessionPanelProps {
  sessionId: string;
  /** Changes every time the panel should be scrolled to again, even for the session already open
   *  (a row clicked twice, a new prompt arriving for it). */
  focusKey: number;
  onClose: () => void;
}

/** The control view for the Live list's selected session, shown under the list: its pending prompt
 *  and an "Open repo window" button. On a narrow (phone) screen, and only while Remote mode is on
 *  (it's what lets a phone act on prompts at all), it scrolls its top to the top of the window
 *  whenever `focusKey` or the session changes, and back to the top of the page once an answer is
 *  accepted. Otherwise the scroll is left alone. Reads the Live list from the shared query cache only
 *  (`auto: false`) — `LiveList`'s own Auto-refresh switch is what drives polling, so this panel
 *  can't keep the list refreshing after it has been switched off. */
export function LiveSessionPanel({ sessionId, focusKey, onClose }: LiveSessionPanelProps) {
  const panelRef = useRef<HTMLElement>(null);
  const liveList = useLive({ auto: false });
  const remoteOn = useMeta().data?.remote_mode.enabled === true;
  // Read at scroll time (an effect below only re-runs on a new selection, not when this flips).
  const shouldScroll = useRef(false);
  shouldScroll.current = remoteOn && isNarrow();
  const session = liveList.data?.sessions.find((s) => s.session_id === sessionId) ?? null;
  const heading = session?.title || session?.name || sessionId;

  // On a phone the list can fill the screen, so line the panel's top up with the top of the window
  // (CSS `scroll-margin-top` keeps it clear of the sticky top bar). Checked at scroll time rather
  // than as an effect dependency, so rotating the phone doesn't scroll.
  useEffect(() => {
    if (!shouldScroll.current) return;
    panelRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }, [sessionId, focusKey]);

  return (
    <section ref={panelRef} className="live-panel" aria-label="Session control">
      <header className="live-panel-header">
        <h2 className="live-panel-title">{heading}</h2>
        <button type="button" className="icon-button" aria-label="Close" onClick={onClose}>
          <CloseIcon />
        </button>
      </header>
      <div className="live-panel-body">
        <LiveControl
          key={sessionId}
          sessionId={sessionId}
          session={session}
          liveLoaded={liveList.data !== undefined}
          onAnswered={() => {
            if (shouldScroll.current) window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      </div>
    </section>
  );
}
