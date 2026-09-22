import type { ServerProblem } from "../api/serverStatus";

const MESSAGES: Record<Exclude<ServerProblem, "none" | "unauthorized">, string> = {
  unreachable: "Can't reach the server. What you see may be out of date.",
  error: "The server reported an error. What you see may be out of date.",
};

/** Shown above the page while a query is failing; the page keeps its last data under it.
 *  It clears itself when polling gets through again. */
export function ServerBanner({ problem, onRetry }: { problem: ServerProblem; onRetry: () => void }) {
  if (problem === "none" || problem === "unauthorized") return null;
  return (
    <div className="banner" role="alert">
      <span>{MESSAGES[problem]}</span>
      <button type="button" className="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}

/** Replaces the page when the server no longer accepts this device (e.g. the token was rotated). */
export function SignInNeeded() {
  return (
    <section className="notice" role="alert">
      <h1>This device isn't signed in</h1>
      <p>
        Open the address that was printed when the server started (it ends in <code>?token=…</code>) on this
        device, or scan its QR code, then reload.
      </p>
    </section>
  );
}
