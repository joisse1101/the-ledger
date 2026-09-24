import type { UseMutationResult } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { useAnswerDecision, useOpenRepo, usePendingDecision } from "../../api/queries";
import type { DecisionAnswer, LiveSession, PendingDecision } from "../../api/types";
import { formatText } from "../../lib/format";

export interface LiveControlProps {
  sessionId: string;
  /** This session's row from the Live list; null while that list is loading or the session has
   *  exited. */
  session: LiveSession | null;
  /** True once the Live list has loaded at least once, so "not in it" can mean "no longer live". */
  liveLoaded: boolean;
}

/** `answer` is owned by LiveControl, not this card: the card unmounts the moment the decision is
 *  gone, and a "too late" (409) result has to outlive that to be seen. */
function DecisionCard({
  decision,
  answer,
}: {
  decision: PendingDecision;
  answer: UseMutationResult<unknown, Error, DecisionAnswer>;
}) {
  const [denying, setDenying] = useState(false);
  const [reason, setReason] = useState("");

  const input = JSON.stringify(decision.tool_input, null, 2);

  const submit = (choice: "allow" | "deny") => {
    const trimmed = reason.trim();
    answer.mutate(choice === "deny" && trimmed ? { decision: choice, reason: trimmed } : { decision: choice });
  };

  return (
    <div className="detail-notice decision-card">
      <p className="detail-heading">Waiting for your decision</p>
      <p>
        <strong>{decision.tool_name}</strong>
      </p>
      <pre className="decision-input">{input}</pre>

      {denying ? (
        <>
          <label className="decision-reason">
            <span className="detail-caption">Reason for denying (optional)</span>
            <input
              type="text"
              value={reason}
              maxLength={200}
              autoFocus
              onChange={(event) => setReason(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") submit("deny");
              }}
            />
          </label>
          <div className="detail-actions">
            <button
              type="button"
              className="button button-danger"
              disabled={answer.isPending}
              onClick={() => submit("deny")}
            >
              {answer.isPending ? "Sending…" : "Confirm deny"}
            </button>
            <button type="button" className="button" disabled={answer.isPending} onClick={() => setDenying(false)}>
              Back
            </button>
          </div>
        </>
      ) : (
        <div className="detail-actions">
          <button type="button" className="button" disabled={answer.isPending} onClick={() => submit("allow")}>
            {answer.isPending ? "Sending…" : "Approve"}
          </button>
          <button type="button" className="button button-danger" disabled={answer.isPending} onClick={() => setDenying(true)}>
            Deny
          </button>
        </div>
      )}
    </div>
  );
}

/** The control-only view opened from the Live list: the session's pending tool-permission
 *  decision (if any) and an "Open repo window" button. Mounting it (and polling the pending
 *  decision) is what tells the server this session is being watched. */
export function LiveControl({ sessionId, session, liveLoaded }: LiveControlProps) {
  const pending = usePendingDecision(sessionId);
  const answer = useAnswerDecision(sessionId);
  const openRepo = useOpenRepo(sessionId);

  const decision = pending.data?.pending_decision ?? null;
  const decisionKey = decision ? `${decision.tool_name}
${JSON.stringify(decision.tool_input)}` : null;

  // A new pending call starts from a clean slate: drop the previous answer's outcome. (Not when the
  // decision merely disappears - that's exactly when a 409 or "sent" note needs to stay visible.)
  useEffect(() => {
    if (decisionKey !== null) answer.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `answer` is a fresh object every render
  }, [decisionKey]);

  const tooLate = answer.error instanceof ApiError && answer.error.status === 409;
  const exited = liveLoaded && session === null;

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
        <p className="detail-caption">Couldn't check for a pending decision. Retrying…</p>
      )}
      {decision ? (
        <DecisionCard decision={decision} answer={answer} />
      ) : (
        !exited && (
          <p className="muted">
            Nothing is waiting on you. A tool-permission prompt will show up here as it happens, if the relay
            hook is installed.
          </p>
        )
      )}

      {tooLate && <p className="detail-caption">This session already moved on, so your answer wasn't used.</p>}
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
