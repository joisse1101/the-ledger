import { formatCount } from "../../lib/format";
import { formatShare, type BreakdownRow } from "../../lib/contextBreakdown";
import { CloseIcon } from "../icons";

export interface ContextBreakdownPanelProps {
  /** 1-based response number. */
  response: number;
  context: number;
  rows: BreakdownRow[];
  onDismiss: () => void;
}

function RowFigures({ row, context }: { row: BreakdownRow; context: number }) {
  return (
    <>
      <span className="breakdown-name">{row.name}</span>
      <span className="breakdown-tokens">
        {row.estimated ? "~" : ""}
        {formatCount(row.tokens)}
      </span>
      <span className="breakdown-share">{formatShare(row.tokens, context)}</span>
    </>
  );
}

/** One response's full context breakdown, pinned under the chart. Categories with items start
 *  collapsed; the parent keys this component by response so selecting another bar collapses them
 *  again. Percentages are of this response's own context. */
export function ContextBreakdownPanel({ response, context, rows, onDismiss }: ContextBreakdownPanelProps) {
  return (
    <section className="breakdown-panel" aria-label={`Context breakdown for response ${response}`}>
      <header className="breakdown-header">
        <p className="detail-heading">
          Response {response}: {formatCount(context)} tokens
        </p>
        <button type="button" className="icon-button" aria-label="Dismiss breakdown" onClick={onDismiss}>
          <CloseIcon />
        </button>
      </header>
      <p className="detail-caption">
        ~ marks an estimate from the transcript; other figures are exact. Percentages are of this response's context.
      </p>
      <ul className="breakdown-rows">
        {rows.map((row) => (
          <li key={row.name}>
            {row.items.length > 0 ? (
              <details>
                <summary className="breakdown-line">
                  <RowFigures row={row} context={context} />
                </summary>
                <ul className="breakdown-items">
                  {row.items.map((item) => (
                    <li key={item.label} className="breakdown-item">
                      <span className="breakdown-name">{item.label}</span>
                      <span className="breakdown-tokens">~{formatCount(item.tokens)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            ) : (
              <div className="breakdown-line">
                <RowFigures row={row} context={context} />
              </div>
            )}
            {row.note && <p className="detail-caption breakdown-note">{row.note}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
