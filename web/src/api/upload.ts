// Uploads one file with progress. `fetch` can't report how much of a request body has been sent, so
// this is the one place that uses XMLHttpRequest; the token, CSRF header and base URL still come
// from the same helpers `apiFetch` uses.

import { ApiError, apiOrigin, CSRF_HEADER, CSRF_VALUE, NetworkError, UnauthorizedError, withQuery } from "./client";
import { getStoredToken } from "./token";
import type { FileEntry } from "./types";

function failureMessage(xhr: XMLHttpRequest): string {
  const fallback = `${xhr.status} ${xhr.statusText}`.trim();
  try {
    const detail = (JSON.parse(xhr.responseText) as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  } catch {
    // not JSON: fall through
  }
  return fallback || "The server reported an error.";
}

/** Sends `file` as the raw request body. `onProgress` gets 0-1. Aborting `signal` cancels the upload
 *  and rejects with an AbortError; the server then removes the partial file. */
export function uploadFile(
  file: File,
  onProgress: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<FileEntry> {
  return new Promise<FileEntry>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", apiOrigin() + withQuery("/api/files", { name: file.name }));
    xhr.setRequestHeader("Accept", "application/json");
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    xhr.setRequestHeader(CSRF_HEADER, CSRF_VALUE);
    const token = getStoredToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) onProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      if (xhr.status === 401) return reject(new UnauthorizedError());
      if (xhr.status < 200 || xhr.status >= 300) return reject(new ApiError(xhr.status, failureMessage(xhr)));
      onProgress(1);
      resolve(JSON.parse(xhr.responseText) as FileEntry);
    };
    xhr.onerror = () => reject(new NetworkError());
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    signal?.addEventListener("abort", () => xhr.abort(), { once: true });

    xhr.send(file);
  });
}
