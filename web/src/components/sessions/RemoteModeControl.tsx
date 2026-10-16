import { useState } from "react";
import { useMeta, useSetRemoteMode } from "../../api/queries";
import type { RemoteMode } from "../../api/types";
import { useNow } from "../../hooks/useNow";
import { formatTimeLeft } from "../../lib/format";
import { Switch } from "../Switch";
import { RemoteQrDialog } from "./RemoteQrDialog";

const STEP_TEXT: Record<NonNullable<RemoteMode["step"]>, string> = {
  docker: "Starting Docker…",
  frontend: "Starting the web interface…",
  gateway: "Starting the gateway…",
};

/** Remote mode on the Live list: a switch (and a button for the sign-in code) on the machine
 *  running the app, read-only text on any other device (only a local request can change it or see
 *  the code - the server refuses everyone else, so showing them controls would be controls that
 *  can only fail). Turning it on can take a minute while Docker and the gateway start. */
export function RemoteModeControl() {
  const meta = useMeta();
  const setRemoteMode = useSetRemoteMode();
  const now = useNow(30_000);
  const [qrOpen, setQrOpen] = useState(false);

  if (!meta.data) return null;
  const { is_local: isLocal, remote_mode: remote } = meta.data;
  // Off the moment it expires, without waiting for the next /api/meta refresh to say so.
  const expiresAt = remote.expires_at ? Date.parse(remote.expires_at) : null;
  const on = remote.enabled && (expiresAt === null || Number.isNaN(expiresAt) || expiresAt > now);
  const timeLeft = on && expiresAt !== null && !Number.isNaN(expiresAt) ? `${formatTimeLeft(expiresAt - now)} left` : null;
  const starting = remote.state === "starting";
  const startingText = starting ? STEP_TEXT[remote.step ?? "docker"] : null;

  if (!isLocal) {
    return (
      <span className="muted sessions-toolbar-caption">
        Remote mode: {on ? "on" : starting ? "starting" : "off"}
        {timeLeft && `, ${timeLeft}`}
      </span>
    );
  }

  return (
    <>
      {/* Checked while starting so it can be switched off to cancel; the caption says it is not on yet. */}
      <Switch
        size="sm"
        checked={on || starting}
        disabled={setRemoteMode.isPending}
        onChange={(checked) => setRemoteMode.mutate(checked)}
        label="Remote mode"
        tooltip={`${startingText ?? timeLeft ?? ""}${startingText || timeLeft ? "\n" : ""}Toggle whether sessions can be remotely controlled`}
      />
      <button type="button" className="button" disabled={!on} onClick={() => setQrOpen(true)}>
        QR code
      </button>
      <RemoteQrDialog open={qrOpen && on} onClose={() => setQrOpen(false)} />
      {startingText && (
        <span role="status" className="detail-caption">
          {startingText}
        </span>
      )}
      {remote.state === "failed" && remote.reason && (
        <span role="alert" className="detail-caption">
          {remote.reason}
        </span>
      )}
      {setRemoteMode.isError && <span className="detail-caption">{setRemoteMode.error.message}</span>}
    </>
  );
}
