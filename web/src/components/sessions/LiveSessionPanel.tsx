import { useEffect, useRef } from "react";
import { useLive } from "../../api/queries";
import { CloseIcon } from "../icons";
import { LiveControl } from "./LiveControl";

export interface LiveSessionPanelProps {
  sessionId: string;
  onClose: () => void;
}

/** The control view for the Live list's selected session, shown under the list: its pending prompt
 *  and an "Open repo window" button. Reads the Live list from the shared query cache only
 *  (`auto: false`) — `LiveList`'s own Auto-refresh switch is what drives polling, so this panel
 *  can't keep the list refreshing after it has been switched off. */
export function LiveSessionPanel({ sessionId, onClose }: LiveSessionPanelProps) {
  const panelRef = useRef<HTMLElement>(null);
  const liveList = useLive({ auto: false });
  const session = liveList.data?.sessions.find((s) => s.session_id === sessionId) ?? null;
  const heading = session?.title || session?.name || sessionId;

  // On a phone the list can fill the screen, so bring a newly selected session's panel into view.
  useEffect(() => {
    panelRef.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [sessionId]);

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
        />
      </div>
    </section>
  );
}
