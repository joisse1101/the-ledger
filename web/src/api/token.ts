// The bearer token a printed link's `?token=` signs this device in with (design.md
// Decision 7): the API has no cookie or query-string handling of its own, so this is
// the frontend's entire sign-in story. Stored in localStorage so it survives reloads;
// wrapped in try/catch since a private window or blocked storage can throw on either
// call, and losing the token just means the next request asks the user to sign in again.

const STORAGE_KEY = "ledger_token";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function setStoredToken(token: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, token);
  } catch {
    // Nothing to fall back to here: the token just won't persist across reloads.
  }
}

/** Called once at startup. A printed link's `?token=` is stored and then stripped from
 *  the address bar (no reload) so it isn't left visible in history (network-access spec,
 *  "Opening a link once signs the device in"). Does nothing if there's no token in the URL. */
export function consumeTokenFromUrl(
  location: Pick<Location, "href" | "pathname" | "search" | "hash"> = window.location,
  history: Pick<History, "replaceState"> = window.history,
): void {
  const url = new URL(location.href);
  const token = url.searchParams.get("token");
  if (!token) return;
  setStoredToken(token);
  url.searchParams.delete("token");
  history.replaceState(null, "", url.pathname + url.search + url.hash);
}
