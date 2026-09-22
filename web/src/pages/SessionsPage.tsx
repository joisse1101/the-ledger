import { useState } from "react";
import { AllList } from "../components/sessions/AllList";
import { LiveList } from "../components/sessions/LiveList";
import type { LiveSession, TranscriptItem } from "../api/types";

// The detail dialog (task 6.4) will consume this selection; for now selecting a
// row just records which session id was clicked.
export function SessionsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelect = (session: LiveSession | TranscriptItem) => {
    setSelectedId(session.session_id);
  };

  return (
    <section>
      <h1>Sessions</h1>
      <LiveList onSelect={handleSelect} />
      <h2>All sessions</h2>
      <AllList onSelect={handleSelect} />
      {selectedId && <p className="muted">Selected: {selectedId}</p>}
    </section>
  );
}
