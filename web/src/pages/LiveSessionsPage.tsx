import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { LiveList } from "../components/sessions/LiveList";
import { LiveSessionPanel } from "../components/sessions/LiveSessionPanel";
import type { LiveSession } from "../api/types";

// The selected session lives in the URL (?session=<id>) rather than component state, so a reload
// or shared link reopens the same control panel.
export function LiveSessionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session");

  const selectSession = useCallback(
    (session: LiveSession) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("session", session.session_id);
        return next;
      });
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

  return (
    <section>
      <h1>Sessions</h1>
      <LiveList onSelect={selectSession} />
      {sessionId && <LiveSessionPanel sessionId={sessionId} onClose={closeSession} />}
    </section>
  );
}
