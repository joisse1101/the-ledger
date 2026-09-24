import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../api/client";
import { useAnswerDecision, useMeta, useOpenRepo, usePendingDecision } from "../../api/queries";
import type { DecisionAnswer, LiveSession } from "../../api/types";
import { formatText } from "../../lib/format";
import { DecisionPrompt } from "./DecisionPrompt";

export interface LiveControlProps {
  sessionId: string;
  /** This session's row from the Live list; null while that list is loading or the session has
   *  exited. */
  session: LiveSession | null;
  /** True once the Live list has loaded at least once, so "not in it" can mean "no longer live". */
  liveLoaded: boolean;
}

/** The control-only view opened from the Live list: the session's oldest pending prompt (a
 *  permission request or a question) and an "Open repo window" button. `answer` lives here, not in
 *  the prompt: the prompt unmounts the moment it is gone, and a "too late" (409) has to outlive that. */
export function LiveControl({ sessionId, session, liveLoaded }: LiveControlProps) {
  const pending = usePendingDecision(sessionId);
  const answer = useAnswerDecision(sessionId);
  const openRepo = useOpenRepo(sessionId);
  const meta = useMeta();

  const decision = pending.data?.pending_decision ?? null;
  const decisionId = decision?.id ?? null;

  // A prompt that vanishes without this view having answered it was resolved elsewhere (the
  // terminal, another device) or timed out: say so instead of just going blank.
  const previousId = useRef<string | null>(null);
  const answeredId = useRef<string | null>(null);
  const [movedOn, setMovedOn] = useState(false);
  useEffect(() => {
    const previous = previousId.current;
    previousId.current = decisionId;
    if (decisionId !== null) {
      // A new prompt starts from a clean slate. (Not when one merely disappears: that is exactly
      // when a 409 or "sent" note needs to stay visible.)
      setMovedOn(false);
      answer.reset();
    } else if (previous !== null && previous !== answeredId.current) {
      setMovedOn(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `answer` is a fresh object every render
  }, [decisionId]);

  const send = (promptId: string, body: DecisionAnswer) => {
    answeredId.current = promptId;
    setMovedOn(false);
    answer.mutate({ promptId, answer: body });
  };

  const tooLate = answer.error instanceof ApiError && answer.error.status === 409;
  const exited = liveLoaded && session === null;
  // Another device can't see prompts at all while Remote mode is off; say why, not just "nothing".
  const hiddenHere = meta.data !== undefined && !meta.data.is_local && !meta.data.remote_mode.enabled;

  return (
    <>
      {session && (
        <dl className="session-recap-stats">
          <div className="session-recap-stat">
            <dt>Project</dt>
            <dd>{formatText(session.project)}</dd>
          </div>
          <div className="session-recap-stat">
            <dt>Status</dt>
            <dd>{formatText(session.status)}</dd>
          </div>
        </dl>
      )}
      {exited && <p className="detail-notice">This session is no longer live.</p>}

      {pending.isError && !decision && (
        <p className="detail-caption">Couldn't check for a pending prompt. Retrying…</p>
      )}
      {decision ? (
        <DecisionPrompt
          key={decision.id}
          decision={decision}
          busy={answer.isPending}
          onAnswer={(body) => send(decision.id, body)}
        />
      ) : (
        !exited && (
          <p className="muted">
            {hiddenHere
              ? "Remote mode is off, so this device isn't shown this session's prompts. Turn it on from the PC that runs the app."
              : "Nothing is waiting on you. A permission prompt or question will show up here as it happens, if the relay hook is installed."}
          </p>
        )
      )}

      {(tooLate || (movedOn && !answer.isSuccess)) && (
        <p className="detail-caption">This session already moved on{tooLate ? ", so your answer wasn't used" : ""}.</p>
      )}
      {answer.isError && !tooLate && <p className="detail-caption">{answer.error.message}</p>}
      {answer.isSuccess && !decision && <p className="detail-caption">Answer sent.</p>}

      <div className="detail-actions">
        <button
          type="button"
          className="button"
          disabled={exited || openRepo.isPending}
          onClick={() => openRepo.mutate()}
        >
          {openRepo.isPending ? "Opening…" : "Open repo window"}
        </button>
      </div>
      {openRepo.isError && <p className="detail-caption">{openRepo.error.message}</p>}
      {openRepo.isSuccess && <p className="detail-caption">Opened on the machine running the app.</p>}
    </>
  );
}
