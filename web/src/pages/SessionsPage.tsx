import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { AllList } from "../components/sessions/AllList";
import { SessionDialog } from "../components/sessions/SessionDialog";
import type { TranscriptItem } from "../api/types";

// The open session lives in the URL (?session=<id>) rather than component state, so a reload or
// shared link reopens the same detail view, and so SessionDialog can stay mounted across
// selections instead of being conditionally rendered (which is what lets a live session's poll
// update it in place).
export function SessionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session");

  const openSession = useCallback(
    (id: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("session", id);
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

  const handleSelectAll = (session: TranscriptItem) => openSession(session.session_id);

  return (
    <section>
      <h1>Sessions</h1>
      <AllList onSelect={handleSelectAll} />
      <SessionDialog sessionId={sessionId} onClose={closeSession} />
    </section>
  );
}
