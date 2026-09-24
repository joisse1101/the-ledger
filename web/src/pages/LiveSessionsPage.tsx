import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLive } from "../api/queries";
import { LiveList } from "../components/sessions/LiveList";
import { LiveSessionPanel } from "../components/sessions/LiveSessionPanel";
import type { LiveSession } from "../api/types";

// The selected session lives in the URL (?session=<id>) rather than component state, so a reload
// or shared link reopens the same control panel.
export function LiveSessionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session");
  // Bumped whenever the panel should scroll into view again, including for the session already open.
  const [focusKey, setFocusKey] = useState(0);

  const openSession = useCallback(
    (id: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("session", id);
        return next;
      });
      setFocusKey((key) => key + 1);
    },
    [setSearchParams],
  );

  const closeSession = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("session");
      return next;
    });
  }, [setSearchParams]);

  // Pop the panel open for a session the moment it starts waiting on a decision. Each prompt is
  // acted on once (so closing the panel doesn't reopen it), and it never yanks the panel away from
  // a session that is itself waiting on the user — they may be mid-answer.
  const live = useLive({ auto: false });
  const sessions = live.data?.sessions;
  const seenPrompts = useRef(new Set<string>());
  useEffect(() => {
    if (!sessions) return;
    const fresh = sessions.find(
      (s) => s.pending_decision && !seenPrompts.current.has(s.pending_decision.id),
    );
    for (const s of sessions) {
      if (s.pending_decision) seenPrompts.current.add(s.pending_decision.id);
    }
    if (!fresh || fresh.session_id === sessionId) return;
    const open = sessions.find((s) => s.session_id === sessionId);
    if (open?.pending_decision) return;
    openSession(fresh.session_id);
  }, [sessions, sessionId, openSession]);

  return (
    <section>
      <h1>Live Sessions</h1>
      <LiveList onSelect={(session: LiveSession) => openSession(session.session_id)} />
      {sessionId && (
        <div className="live-panel-area">
          <LiveSessionPanel sessionId={sessionId} focusKey={focusKey} onClose={closeSession} />
        </div>
      )}
    </section>
  );
}
