import { useMeta, useSetRemoteMode } from "../../api/queries";
import { useNow } from "../../hooks/useNow";
import { formatTimeLeft } from "../../lib/format";
import { Switch } from "../Switch";

/** Remote mode on the Live list: a switch on the machine running the app, read-only text on any
 *  other device (only a local request can change it - the server refuses everyone else, so
 *  showing them a switch would be a control that can only fail). */
export function RemoteModeControl() {
  const meta = useMeta();
  const setRemoteMode = useSetRemoteMode();
  const now = useNow(30_000);

  if (!meta.data) return null;
  const { is_local: isLocal, remote_mode: remote } = meta.data;
  // Off the moment it expires, without waiting for the next /api/meta refresh to say so.
  const expiresAt = remote.expires_at ? Date.parse(remote.expires_at) : null;
  const on = remote.enabled && (expiresAt === null || Number.isNaN(expiresAt) || expiresAt > now);
  const timeLeft = on && expiresAt !== null && !Number.isNaN(expiresAt) ? `${formatTimeLeft(expiresAt - now)} left` : null;

  if (!isLocal) {
    return (
      <span className="muted sessions-toolbar-caption">
        Remote mode: {on ? "on" : "off"}
        {timeLeft && `, ${timeLeft}`}
      </span>
    );
  }

  return (
    <>
      <Switch
        size="sm"
        checked={on}
        disabled={setRemoteMode.isPending}
        onChange={(checked) => setRemoteMode.mutate(checked)}
        label="Remote mode"
        tooltip={`${timeLeft ? `${timeLeft}\n` : ""}Toggle whether the Ledger can be remotely accessed`}
      />
      {setRemoteMode.isError && <span className="detail-caption">{setRemoteMode.error.message}</span>}
    </>
  );
}
