import { useMeta, useSetAutoApprove } from "../../api/queries";
import type { LiveSession } from "../../api/types";
import { Switch } from "../Switch";

/** One session's auto-approve in its control view: a switch on the machine running the app,
 *  read-only text on any other device (the server refuses everyone else, so a switch there could
 *  only fail). Shown nowhere until the app has seen a prompt relayed - without the relay hook it
 *  could never act. */
export function AutoApproveControl({ session }: { session: LiveSession | null }) {
  const meta = useMeta();
  const setAutoApprove = useSetAutoApprove(session?.session_id ?? "");

  if (!session || !meta.data?.relay_hook_seen) return null;

  if (!meta.data.is_local) {
    return session.auto_approve ? <span className="muted sessions-toolbar-caption">Auto-approve on</span> : null;
  }

  return (
    <>
      <Switch
        size="sm"
        checked={session.auto_approve}
        disabled={setAutoApprove.isPending}
        onChange={(checked) => setAutoApprove.mutate(checked)}
        label="Auto-approve"
        tooltip="Approve this session's permission prompts automatically. Questions, plans and risky shell commands still wait for you."
      />
      {setAutoApprove.isError && <span className="detail-caption">{setAutoApprove.error.message}</span>}
    </>
  );
}
