import { useEffect, useRef, useState } from "react";
import { LIVE_POLL_MS, useSession } from "../../api/queries";
import type { Compaction, SessionDetail, SessionRecap, Turn } from "../../api/types";
import { formatContext, formatCost, formatCount, formatDateTime, formatText, formatTime } from "../../lib/format";
import { humanizeTokens } from "../../lib/tokens";
import { CloseIcon } from "../icons";
import { TokensChart } from "./TokensChart";

export interface SessionDialogProps {
  /** null when no session is selected: the dialog stays mounted (so it can close itself with an
   *  animation-friendly transition later) but closed. */
  sessionId: string | null;
  /** All list selections get the recap block; Live list selections don't (per spec). */
  from: "live" | "all";
  onClose: () => void;
}

function compactionCaptions(detail: SessionDetail): string[] {
  return detail.compactions.map((c) => {
    const was = c.pre_tokens ? `, was ${humanizeTokens(c.pre_tokens)}` : "";
    const how = c.trigger ? ` (${c.trigger})` : "";
    return `Compacted${how} after response ${c.position}${was}`;
  });
}

interface HistoryRow {
  number: number;
  time: string;
  new: number;
  cacheRead: number;
  cacheWritten: number;
  output: number;
  note: string;
}

function historyRows(turns: Turn[], compactions: Compaction[]): HistoryRow[] {
  const compactedBefore = new Set(compactions.map((c) => c.position));
  return turns.map((turn, index) => {
    const notes: string[] = [];
    if (compactedBefore.has(index)) notes.push("compacted before this response");
    if (turn.cache_miss) notes.push("cache miss");
    return {
      number: index + 1,
      time: formatTime(turn.timestamp),
      new: turn.new,
      cacheRead: turn.cache_read,
      cacheWritten: turn.cache_written,
      output: turn.output,
      note: notes.join(", "),
    };
  });
}

function Recap({ recap }: { recap: SessionRecap }) {
  const hasSummary = recap.title || recap.last_message || recap.first_prompt;
  const stats: [string, string][] = [];
  if (recap.started_at) stats.push(["Started", formatDateTime(recap.started_at)]);
  if (recap.updated_at) stats.push(["Last updated", formatDateTime(recap.updated_at)]);
  if (recap.message_count != null) stats.push(["Messages", formatCount(recap.message_count)]);
  if (recap.avg_tokens_per_message != null) stats.push(["Tokens per message", formatCount(recap.avg_tokens_per_message)]);
  if (recap.cost != null) stats.push(["Cost", formatCost(recap.cost)]);

  return (
    <div className="session-recap">
      {hasSummary ? (
        <>
          {recap.title && (
            <>
              <p className="detail-caption">Session title</p>
              <p>{recap.title}</p>
            </>
          )}
          {recap.last_message ? (
            <>
              <p className="detail-caption">Last message from Claude</p>
              <p>{recap.last_message}</p>
            </>
          ) : recap.first_prompt ? (
            <>
              <p className="detail-caption">First prompt</p>
              <p>{recap.first_prompt}</p>
            </>
          ) : null}
        </>
      ) : (
        <p className="muted">No information available for this session yet.</p>
      )}
      {stats.length > 0 && (
        <dl className="session-recap-stats">
          {stats.map(([label, value]) => (
            <div key={label} className="session-recap-stat">
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

function Detail({ detail }: { detail: SessionDetail }) {
  if (detail.turns.length === 0) {
    return <p className="muted">This session hasn't had a response from Claude yet.</p>;
  }

  const lastContext = detail.turns[detail.turns.length - 1].context;
  const attribution = detail.attribution;
  const since = detail.compactions.length > 0 ? "the last compaction" : "the start of the session";

  return (
    <>
      <div className="session-metric">
        <span className="detail-caption">Current context</span>
        <span className="session-metric-value">{formatContext(lastContext)} tokens</span>
        <span className="muted">
          {lastContext.toLocaleString()} tokens sent on the latest response, across {detail.turns.length} responses.
        </span>
      </div>

      <div>
        <p className="detail-heading">Tokens per response</p>
        <p className="detail-caption">
          Each bar is what one request sent: newly sent input plus cached tokens read and written.
        </p>
        <TokensChart turns={detail.turns} />
        {compactionCaptions(detail).map((caption) => (
          <p key={caption} className="detail-caption">
            {caption}
          </p>
        ))}
      </div>

      <details className="detail-section">
        <summary>All responses</summary>
        <div className="list-table-scroll">
          <table className="detail-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Time</th>
                <th data-align="end">New</th>
                <th data-align="end">Cache read</th>
                <th data-align="end">Cache written</th>
                <th data-align="end">Output</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {historyRows(detail.turns, detail.compactions).map((row) => (
                <tr key={row.number}>
                  <td>{row.number}</td>
                  <td>{row.time}</td>
                  <td data-align="end">{formatCount(row.new)}</td>
                  <td data-align="end">{formatCount(row.cacheRead)}</td>
                  <td data-align="end">{formatCount(row.cacheWritten)}</td>
                  <td data-align="end">{formatCount(row.output)}</td>
                  <td>{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <div>
        <p className="detail-heading">What filled the context</p>
        {attribution.by_tool.length === 0 ? (
          <p className="detail-caption">Nothing has been added since the session started or was last compacted.</p>
        ) : (
          <>
            <p className="detail-caption">
              Growth since {since}, credited to the tool whose result caused it: {attribution.floor.toLocaleString()} at the
              first response + {(attribution.current - attribution.floor).toLocaleString()} added ={" "}
              {attribution.current.toLocaleString()} now.
            </p>
            <div className="list-table-scroll">
              <table className="detail-table">
                <thead>
                  <tr>
                    <th>Tool</th>
                    <th data-align="end">Tokens</th>
                    <th data-align="end">Uses</th>
                  </tr>
                </thead>
                <tbody>
                  {attribution.by_tool.map((g) => (
                    <tr key={g.tool}>
                      <td>{formatText(g.tool)}</td>
                      <td data-align="end">{formatCount(g.tokens)}</td>
                      <td data-align="end">{formatCount(g.uses)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {attribution.largest.length > 0 && (
              <>
                <p className="detail-heading">Largest single increases</p>
                <div className="list-table-scroll">
                  <table className="detail-table">
                    <thead>
                      <tr>
                        <th>Response</th>
                        <th data-align="end">Tokens</th>
                        <th>Tool</th>
                        <th>Hint</th>
                      </tr>
                    </thead>
                    <tbody>
                      {attribution.largest.map((inc) => (
                        <tr key={inc.index}>
                          <td>{inc.index + 1}</td>
                          <td data-align="end">{formatCount(inc.tokens)}</td>
                          <td>{formatText(inc.tool)}</td>
                          <td>{formatText(inc.hint)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </>
  );
}

/** The session detail view: a native `<dialog>` kept mounted so opening/closing never remounts
 *  it, which is what lets a Live poll update its content in place without disturbing scroll
 *  position (see design.md's "detail view" decision). Delete (task 6.6) isn't wired up yet. */
export function SessionDialog({ sessionId, from, onClose }: SessionDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [live, setLive] = useState(false);

  useEffect(() => {
    setLive(false);
  }, [sessionId]);

  const session = useSession(sessionId, { refetchMs: live ? LIVE_POLL_MS : undefined });

  useEffect(() => {
    if (session.data) setLive(session.data.live);
  }, [session.data]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (sessionId && !dialog.open) {
      dialog.showModal();
    } else if (!sessionId && dialog.open) {
      dialog.close();
    }
  }, [sessionId]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const handleClose = () => onClose();
    dialog.addEventListener("close", handleClose);
    return () => dialog.removeEventListener("close", handleClose);
  }, [onClose]);

  const data = session.data;
  const heading = data?.recap?.title || sessionId || "Session";

  return (
    <dialog ref={dialogRef} className="session-dialog" aria-label="Session detail">
      <div className="session-dialog-scroll">
        <header className="session-dialog-header">
          <h2 className="session-dialog-title">{heading}</h2>
          <button type="button" className="icon-button" aria-label="Close" onClick={() => dialogRef.current?.close()}>
            <CloseIcon />
          </button>
        </header>
        <div className="session-dialog-body">
          {sessionId && (
            <>
              {session.isPending && <p className="muted">Loading…</p>}
              {session.isError && (
                <div className="detail-notice">
                  Couldn't load this session.{" "}
                  <button type="button" className="button" onClick={() => session.refetch()}>
                    Retry
                  </button>
                </div>
              )}
              {data && (
                <>
                  {from === "all" && data.recap && <Recap recap={data.recap} />}
                  {!data.readable && <p className="detail-notice">Couldn't read this session's transcript.</p>}
                  {data.readable && data.detail && <Detail detail={data.detail} />}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </dialog>
  );
}
