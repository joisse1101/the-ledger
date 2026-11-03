# Frontend: files

This page explains how the Files page is built: the file-drop folder on the PC, with upload, download and delete. Read it before changing them. Remote mode is defined in the [Glossary](Glossary.md#remote-mode).

> Requirements live in the file-drop capability spec (in the `add-file-drop` change until it is archived, then in the specs folder). This page describes how the code meets them, not what it must do.

## Where the code is

- `web/src/pages/FilesPage.tsx` is the page.
- `web/src/api/upload.ts` does uploads.
- `web/src/lib/download.ts` starts downloads.

## Availability

The page exists only while Remote mode is on. `Nav` shows the Files link only when `useMeta().remote_mode.enabled`, and the page renders `<Navigate to="/">` when it is off.

If Remote mode ends while the page is open, the next request the server refuses (403) makes the page re-read `/api/meta`, which then sends the user home. The server refuses file requests regardless, so hiding is only UX.

## Upload

The upload control is a file input (`multiple`) styled as a button. Files go one at a time, because parallel uploads only slow each other down on a hotspot. Each is sent as a raw `PUT /api/files?name=` body through `web/src/api/upload.ts`.

`fetch` cannot report how much of a body has been sent, so that file uses `XMLHttpRequest` for per-file progress. The token, CSRF header and base URL come from the same helpers as `apiFetch`. A failure shows the server's message next to that file, for example that the PC's disk is full.

## List and download

`useFiles` lists the folder with `formatBytes` sizes. Download calls `useDownloadFile`, which asks `POST /api/files/{name}/download-link` for a single-use link. It hands the link to the browser through `startDownload` (`web/src/lib/download.ts`), so the file streams to disk instead of being held in the page. The link is fetched at click time and never kept.

## Delete

Delete is shown only when `useMeta().is_local` and is confirmed with `ConfirmDialog`. The API refuses a remote delete anyway.
