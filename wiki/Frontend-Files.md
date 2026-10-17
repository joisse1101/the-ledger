# Frontend: files

> Requirements live in the file-drop capability spec (in the `add-file-drop` change until it is archived, then in the specs folder). This page describes how the code meets them, not what it must do.

- **Files** (`web/src/pages/FilesPage.tsx`): the file-drop folder on the PC. It exists only while Remote
  mode is on: `Nav` shows the Files link only when `useMeta().remote_mode.enabled`, and the page renders
  `<Navigate to="/">` when it is off. If Remote mode ends while the page is open, the next request the
  server refuses (403) makes the page re-read `/api/meta`, which then sends the user home; the server
  refuses file requests regardless, so hiding is only UX.
- **Upload**: a file input (`multiple`) styled as a button. Files go one at a time (parallel uploads only
  slow each other down on a hotspot), each as a raw `PUT /api/files?name=` body through
  `web/src/api/upload.ts`. `fetch` can't report how much of a body has been sent, so that file uses
  `XMLHttpRequest` for per-file progress; the token, CSRF header and base URL come from the same
  helpers as `apiFetch`. A failure shows the server's message next to that file (for example the PC's
  disk is full).
- **List and download**: `useFiles` lists the folder with `formatBytes` sizes. Download calls
  `useDownloadFile`, which asks `POST /api/files/{name}/download-link` for a single-use link and hands
  it to the browser through `startDownload` (`web/src/lib/download.ts`), so the file streams to disk
  instead of being held in the page; the link is fetched at click time and never kept.
- **Delete**: shown only when `useMeta().is_local` and confirmed with `ConfirmDialog`; the API refuses
  a remote delete anyway.
