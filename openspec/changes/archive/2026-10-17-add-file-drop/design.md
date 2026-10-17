## Context

See proposal.md for motivation. Constraints from the current code:

- Every request to a device other than the PC already passes `SecurityMiddleware` (token, and an
  `X-Requested-With: ledger` header on non-GET). Gateway traffic always counts as remote.
- Remote mode state lives in `PendingDecisions` (`remote_mode_enabled()`, `expires_at`, 8 h TTL) and
  is already exposed to the frontend as `remote_mode` in `GET /api/meta`.
- Routes in `server.py` stay thin; data modules (`claude_*.py`) import no web code.
- `gateway/nginx.conf.template` has no `client_max_body_size`, so Nginx rejects bodies over 1 MB
  with 413, and it buffers request bodies to disk by default.
- The frontend calls the backend only through `apiFetch`; `fetch` cannot report upload progress.

## Goals / Non-Goals

**Goals:**
- Large files stream to and from disk with flat memory use, over the existing gateway.
- The Remote-mode gate and the local-only delete are enforced in the routes, not the UI.
- No new credential, no new port, no new dependency.

**Non-Goals:**
- Resumable or chunked uploads, folder trees, sharing links, previews, or per-file permissions.
- A second QR or a transfer-only token (rejected: one sign-in for everything keeps it simple).
- Browsing any location on the PC other than the drop folder.

## Decisions

**1. Pure `api/file_drop.py` plus thin routes.** The module owns the folder location, listing, name
sanitising, collision handling, the streamed save and delete. It takes the folder as an argument and
an iterator of byte chunks, and imports no FastAPI, so tests drive it with a temp directory. Routes
only translate to HTTP errors.

**2. Upload is a raw streamed body, `PUT /api/files?name=<file name>`.** The route iterates
`request.stream()` and writes chunks as they arrive. Alternative: multipart form upload, rejected
because it needs the `python-multipart` dependency and is awkward to stream. The name travels in the
query, so the body is exactly the file's bytes.

**3. Safe, atomic save.** The chunks go to a temp file in a `.incoming/` subfolder of the drop
folder (same volume, so the final step is a rename, and the subfolder is never listed). On success
the file is placed with `os.link` + unlink of the temp, which fails if the target exists, so two
uploads of one name can never overwrite each other; on `FileExistsError` the name gets ` (1)`,
` (2)`, ... before the extension. On any error, client disconnect or disk-full the temp file is
removed in a `finally`. Alternative: write to the final name directly, rejected because an
interrupted upload would leave a truncated file in the list.

**4. Name sanitising happens once, at the boundary.** Strip any directory part, replace characters
Windows rejects (`<>:"/\|?*` and control characters), trim trailing dots and spaces, avoid reserved
device names (`CON`, `NUL`, ...), cap the length, and fall back to `file` for an empty result.
Download and delete take a name and resolve it as `drop_dir / name`; they refuse anything whose
resolved parent is not the drop folder or that is not a regular file. The list returns regular files
only, so subfolders (including `.incoming`) never appear.

**5. Download is a `FileResponse`.** It streams from disk, sets `Content-Disposition: attachment`
with the file name, and supports range requests, which matter for big files on a flaky link.

**5b. Browsers can't send the bearer header on a download, so downloads start from a single-use
link.** `POST /api/files/{name}/download-link` (token, Remote-mode gate, file must exist) returns
`/api/files/download/<ticket>`. A small in-memory `DownloadTickets` store in `file_drop.py`
(injectable clock, no web imports) issues a `secrets.token_urlsafe` ticket bound to one file name,
valid for 60 seconds and redeemable once. `GET /api/files/download/{ticket}` redeems it and serves
the file as in decision 5, with `Cache-Control: no-store`; an unknown, used or expired ticket is
refused with 403. `SecurityMiddleware` lets exactly that GET path shape through without a bearer,
which is a path match only: the ticket, not the middleware, is the credential, and the route still
applies the Remote-mode gate. Tickets are never logged. Alternatives: fetch into a blob (no backend
change, but a large file exhausts a phone's memory and shows no native progress); a `?token=` query
on any URL (rejected: it would reopen the whole API to leaked URLs); a service worker adding the
header (far more machinery). The token-less `GET /api/files/{name}` stays bearer-only, for scripts.

**6. Remote-mode gate as one route dependency.** A small dependency calls
`decisions.remote_mode_enabled()` and raises 403 ("Remote mode is off") for every file route,
local requests included. This differs from `_can_see_prompts`, which lets the PC through, because
the spec hides the whole feature outside Remote mode. Delete additionally calls `is_local` and
raises 403 otherwise, the same shape as the session delete route. The folder location comes from
the `LEDGER_TRANSFER_DIR` environment variable, read at startup like the other `LEDGER_*` settings,
defaulting to `api/.ledger/transfer/` (already git-ignored via `.ledger/`).

**7. Gateway settings on the file route only.** Add `location /api/files` (more specific than
`/api/`) with `client_max_body_size 0`, `proxy_request_buffering off`, `proxy_buffering off` and
long `proxy_read_timeout`/`proxy_send_timeout`, so Nginx streams rather than spooling a 2 GB video
to its own disk first. Other API routes keep the default 1 MB limit.

**8. Frontend.** A `FilesPage` plus a nav entry filtered on `meta.remote_mode.enabled`; the route
redirects home when Remote mode is off, and the shell's meta polling makes a mid-session switch-off
take effect. Upload uses `XMLHttpRequest` for per-file progress, added beside `apiFetch` in
`web/src/api/` so the token, `X-Requested-With` header and base URL still come from one place. The
list is a query that refetches after upload/delete. The delete control renders only when
`meta.is_local`; the server check is the real boundary. Types mirror the server JSON in `types.ts`.

## Risks / Trade-offs

- [A phone sleeping or leaving the hotspot kills an upload] → the temp file is cleaned up and the
  page shows the failure; no resume in v1.
- [The same token opens the whole Ledger, not only Files] → accepted for simplicity; unchanged trust
  model on a network the user controls. Isolation (separate port and token) is a possible later
  change.
- [A download link leaks (screenshot, history, referrer)] → it dies after one use or 60 seconds,
  names one file, and is useless once Remote mode is off; the response is `no-store`.
- [Disk fills during an upload] → catch `OSError`, remove the temp file, return 507 with a clear
  message instead of leaving a partial file.
- [Remote mode ends after 8 h or on switch-off with an upload running] → the running request
  completes or fails on its own; new requests are refused. Acceptable.
- [Self-signed certificate and large uploads on mobile Safari/Chrome] → certificate is accepted
  once per device as today; verify a large upload on a real phone before calling it done.
- [Frontend dev/preview proxy might buffer or cap bodies] → check that `vite` forwards `/api/files`
  as a stream when used locally; the gateway goes straight to the backend for `/api/`.

## Open Questions

- Should a successful download or upload write a log line? Structured logging at the route boundary
  is the default; whether to expose a history in the UI can wait.
