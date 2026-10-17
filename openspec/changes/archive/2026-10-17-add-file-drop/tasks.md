## 1. Drop-folder module (api)

- [x] 1.1 Add `api/file_drop.py` with folder resolution (`LEDGER_TRANSFER_DIR`, default `api/.ledger/transfer/`, created on first use) and `list_files()` returning regular files only, newest first; verify with `api/tests/test_file_drop.py` (empty folder, ordering, subfolder and `.incoming` not listed)
- [x] 1.2 Add name sanitising (separators, Windows-invalid characters, reserved names, trailing dots/spaces, length cap, empty fallback); verify with parametrised unit tests including `../../x`, `a\b`, `CON.txt`, `""`
- [x] 1.3 Add `save_stream()`: write chunks to `.incoming/`, place with `os.link` so an existing name is never overwritten (` (1)`, ` (2)` suffix), always remove the temp file on error or disconnect; verify with tests for a normal save, a name collision, a raising chunk iterator leaving nothing behind, and a disk-full `OSError`
- [x] 1.4 Add `resolve_existing()` and `delete_file()` that accept a bare name only and refuse anything outside the folder or not a regular file; verify with traversal and missing-file tests

## 2. Routes (api)

- [x] 2.1 Add the Remote-mode gate dependency (403 "Remote mode is off" for every file route, local requests included) and `GET /api/files`; verify with route tests for mode off (403 from loopback and from a token holder) and mode on (list returned)
- [x] 2.2 Add `PUT /api/files?name=` streaming `request.stream()` into `save_stream()` (507 on disk full, no partial file on client disconnect); verify with a route test uploading a multi-chunk body and an aborted-stream test
- [x] 2.3 Add `GET /api/files/{name}` as a `FileResponse` attachment (range requests, 404 when gone) and `DELETE /api/files/{name}` requiring `is_local`; verify with tests for byte-identical download, 404, delete from loopback, and 403 delete with a valid token from a non-local request
- [x] 2.4 Log upload, download and delete at the route boundary as structured key/value lines without file contents; verify with a caplog assertion
- [x] 2.5 Run `cd api; pytest` and confirm the whole suite passes
- [x] 2.6 Add `DownloadTickets` to `api/file_drop.py` (issue bound to a file name, single use, 60 s expiry, injectable clock); verify with unit tests for redeem-once, expiry, unknown ticket and purge of expired tickets
- [x] 2.7 Add `POST /api/files/{name}/download-link` and `GET /api/files/download/{ticket}` (Remote-mode gate, `no-store`, 403 on a bad ticket, ticket never logged) and let `SecurityMiddleware` pass exactly that GET path shape without a bearer; verify with route tests for link-works-once, expiry, no token to ask for a link, a link not opening any other path, Remote mode off, and `test_security.py` cases for the path match
- [x] 2.8 Re-run `cd api; pytest` and confirm the whole suite passes

## 3. Gateway

- [x] 3.1 Add a `location /api/files` block to `gateway/nginx.conf.template` (`client_max_body_size 0`, `proxy_request_buffering off`, `proxy_buffering off`, long read/send timeouts, same forwarded headers); verify the rendered config with `nginx -t` inside the built image
- [x] 3.2 With Remote mode on, upload a file larger than 1 MB through `https://<address>:<port>` and confirm it is saved intact (hash matches), proving no 413

## 4. Frontend

- [x] 4.1 Add `FileEntry` and list types to `web/src/api/types.ts`, a `useFiles` query and delete mutation in `queries.ts`, and an XHR-based `uploadFile` helper beside `apiFetch` that reports progress and sends the token and `X-Requested-With` header; verify with Vitest tests for progress callbacks, headers, and error propagation
- [x] 4.2 Add `FilesPage` (file picker, per-file progress and failure state, list with size and modified time, download buttons that request a single-use link and navigate to it, empty state) with a CSS module and design tokens; verify with component tests for listing, upload progress, the download-link request and empty state
- [x] 4.3 Show the delete control only when `meta.is_local`, behind `ConfirmDialog`; verify with a test that a non-local meta hides it
- [x] 4.4 Add the `/files` route and a Files nav entry shown only when `meta.remote_mode.enabled`, with the route redirecting home when it is off (including when it turns off while open); verify with tests for hidden/shown nav and the redirect
- [x] 4.5 Run `cd web; npm test; npm run build` and confirm both pass

## 5. Docs and real-device check

- [x] 5.1 Update `wiki/Backend-API-Routes.md`, `wiki/Gateway.md`, a frontend page doc, `wiki/Home.md` and the `CLAUDE.md` routing table for the new page and routes; verify `cd api; python check_docs.py` passes
- [x] 5.2 On the phone hotspot, with the PC joined to it only: turn Remote mode on, scan the QR, upload and download a large file, and confirm the Files page is absent after turning Remote mode off; record the result (and the address the QR used) in the change's notes
  - Result (2026-10-17): all behaviour worked as specified on a real phone. The QR used a `10.60.x.x` address (the hotspot's own private range, not `192.168.x.x`), and address detection picked the right interface.
