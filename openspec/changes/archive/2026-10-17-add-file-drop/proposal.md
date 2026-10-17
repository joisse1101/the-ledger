## Why

There is no cable-free way to move a file between the PC and a phone. The Ledger already reaches a
phone over the LAN (HTTPS gateway, access token, QR sign-in) and that traffic never leaves the
local network, so it can carry files too, without a cloud service or an extra app.

## What Changes

- Add a **Files** page: one shared drop folder on the PC. From any signed-in device the user can
  list the folder, upload files into it and download files from it.
- The page and its endpoints exist **only while Remote mode is on**. With Remote mode off the nav
  hides the page and the endpoints refuse every request, local or not.
- Uploads and downloads stream to and from disk, so large files (videos, archives) work. The
  gateway's request-size limit and buffering are raised/disabled for the upload route.
- Downloads start from a single-use link that lives about a minute: the page asks the API (with the
  token) for it, then the browser streams the file natively, with no whole-file buffering in the page.
- Deleting a file from the drop folder requires a local request, like session and project deletes.
- The folder is fixed server-side (`api/.ledger/transfer/` by default, overridable by an
  environment variable). The client never supplies a path.

No new sign-in: the existing token and QR give access, so a device that can open the Ledger can use
Files and the other way round.

## Capabilities

### New Capabilities
- `file-drop`: the Files page and its list/upload/download/delete endpoints, the single drop folder,
  and the Remote-mode gate.

### Modified Capabilities
- `network-access`: "Other devices must present an access token for data" gains one narrow
  exception: a single-use, short-lived file-drop download link, because a browser download can't
  carry the bearer header.

## Impact

- `api/`: new module for the drop folder (pure file logic, no web imports), new routes in
  `server.py`, a one-path exemption in `security.py` for the download link, tests.
- `web/`: new `FilesPage`, a nav entry shown only when `remote_mode.enabled`, API client/query/type
  additions, tests.
- `gateway/nginx.conf.template`: `client_max_body_size` and unbuffered request bodies on the file
  upload route, longer timeouts.
- `wiki/`: Backend-API-Routes, Frontend page doc, Gateway; `CLAUDE.md` routing table row.
- No new dependencies expected (FastAPI streaming upload needs `python-multipart` only if form
  uploads are used; the design uses a raw streamed body instead).
