import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { LiveList } from "../components/sessions/LiveList";
import { SessionDialog } from "../components/sessions/SessionDialog";
import type { LiveSession } from "../api/types";

// The open session lives in the URL (?session=<id>&from=live|all) rather than component state,
// so a reload or shared link reopens the same detail view, and so SessionDialog can stay mounted
// across selections instead of being conditionally rendered (which is what lets a Live poll
// update it in place).
export function LiveSessionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session");
  const from = searchParams.get("from") === "all" ? "all" : "live";

  const openSession = useCallback(
    (id: string, source: "live" | "all") => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("session", id);
        next.set("from", source);
        return next;
      });
    },
    [setSearchParams],
  );

  const closeSession = useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("session");
      next.delete("from");
      return next;
    });
  }, [setSearchParams]);

  const handleSelectLive = (session: LiveSession) => openSession(session.session_id, "live");

  return (
    <section>
      <h1>Sessions</h1>
      <LiveList onSelect={handleSelectLive} />
      <SessionDialog sessionId={sessionId} from={from} onClose={closeSession} />
    </section>
  );
}
