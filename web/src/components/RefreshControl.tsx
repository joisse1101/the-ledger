import { useMeta, useRefresh } from "../api/queries";
import { formatTime } from "../lib/format";
import { RefreshIcon } from "./icons";

/** The one refresh control: rescans Claude Code's files and shows when that last happened. */
export function RefreshControl() {
  const meta = useMeta();
  const refresh = useRefresh();

  return (
    <div className="refresh">
      <span className="refresh-caption" role="status">
        {refresh.isError ? (
          <span className="refresh-failed">Refresh failed</span>
        ) : (
          <>
            <span className="refresh-label">Last refreshed: </span>
            <time dateTime={meta.data?.refreshed_at ?? undefined}>{formatTime(meta.data?.refreshed_at)}</time>
          </>
        )}
      </span>
      <button
        type="button"
        className="icon-button"
        onClick={() => refresh.mutate()}
        disabled={refresh.isPending}
        aria-label="Refresh data"
        title="Rescan Claude Code's files"
      >
        <span className={refresh.isPending ? "spin" : undefined}>
          <RefreshIcon />
        </span>
      </button>
    </div>
  );
}
