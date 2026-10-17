import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Navigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { keys, useDeleteFile, useDownloadFile, useFiles, useMeta, useUploadFile } from "../api/queries";
import type { FileEntry } from "../api/types";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { formatBytes, formatDateTime } from "../lib/format";
import styles from "./FilesPage.module.css";

interface UploadItem {
  id: number;
  name: string;
  fraction: number;
  state: "uploading" | "done" | "failed";
  error?: string;
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

/** The file-drop folder on the PC: upload from this device, download what is there. Exists only while
 *  Remote mode is on - with it off the navigation hides this page and the server refuses its requests,
 *  so a visit sends the user home. */
export function FilesPage() {
  const client = useQueryClient();
  const meta = useMeta();
  const remoteOn = meta.data?.remote_mode.enabled === true;
  const isLocal = meta.data?.is_local === true;
  const files = useFiles(remoteOn);
  const upload = useUploadFile();
  const download = useDownloadFile();
  const remove = useDeleteFile();

  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [toDelete, setToDelete] = useState<FileEntry | null>(null);
  const nextId = useRef(0);

  // The server says no the moment Remote mode ends; re-read the mode now rather than at the next poll.
  const refused = files.error instanceof ApiError && files.error.status === 403;
  useEffect(() => {
    if (refused) void client.invalidateQueries({ queryKey: keys.meta });
  }, [refused, client]);

  if (meta.data && !remoteOn) return <Navigate to="/" replace />;
  if (!meta.data) return null;

  const patch = (id: number, change: Partial<UploadItem>) =>
    setUploads((items) => items.map((item) => (item.id === id ? { ...item, ...change } : item)));

  async function onPick(event: ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    event.target.value = ""; // so picking the same file again still fires
    const items = picked.map((file) => ({
      file,
      item: { id: nextId.current++, name: file.name, fraction: 0, state: "uploading" } as UploadItem,
    }));
    setUploads((current) => [...current, ...items.map(({ item }) => item)]);
    // One at a time: on a hotspot, parallel uploads just slow each other down.
    for (const { file, item } of items) {
      try {
        await upload.mutateAsync({ file, onProgress: (fraction) => patch(item.id, { fraction }) });
        patch(item.id, { state: "done", fraction: 1 });
      } catch (error) {
        patch(item.id, { state: "failed", error: messageOf(error) });
      }
    }
  }

  function confirmDelete() {
    if (!toDelete) return;
    remove.mutate(toDelete.name, {
      onSuccess: () => setToDelete(null),
    });
  }

  const entries = files.data?.files ?? [];

  return (
    <section>
      <h1>Files</h1>
      <p className={styles.hint}>
        A shared folder on the PC. Anything uploaded here lands in it; anything in it can be downloaded.
      </p>

      <label className={`button ${styles.pick}`}>
        Upload files
        <input type="file" multiple className={styles.input} onChange={(event) => void onPick(event)} />
      </label>

      {uploads.length > 0 && (
        <ul className={styles.uploads} aria-label="Uploads">
          {uploads.map((item) => (
            <li key={item.id} className={styles.upload}>
              <span className={styles.name}>{item.name}</span>
              {item.state === "uploading" && (
                <progress value={item.fraction} max={1} aria-label={`Uploading ${item.name}`} />
              )}
              {item.state === "done" && <span className={styles.ok}>Uploaded</span>}
              {item.state === "failed" && (
                <span role="alert" className={styles.failed}>
                  Failed: {item.error}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {files.isError && !refused && <p role="alert">Couldn't load the folder: {messageOf(files.error)}</p>}
      {files.isSuccess && entries.length === 0 && <p className={styles.empty}>The folder is empty.</p>}
      {entries.length > 0 && (
        <ul className={styles.list} aria-label="Files in the folder">
          {entries.map((entry) => (
            <li key={entry.name} className={styles.row}>
              <div className={styles.meta}>
                <span className={styles.name}>{entry.name}</span>
                <span className={styles.detail}>
                  {formatBytes(entry.size)} · {formatDateTime(entry.modified)}
                </span>
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className="button"
                  disabled={download.isPending}
                  onClick={() =>
                    download.mutate(entry.name, { onError: () => void files.refetch() })
                  }
                >
                  Download
                </button>
                {isLocal && (
                  <button type="button" className="button button-danger" onClick={() => setToDelete(entry)}>
                    Delete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {download.isError && <p role="alert">Couldn't download: {messageOf(download.error)}</p>}

      <ConfirmDialog
        open={toDelete !== null}
        title="Delete this file?"
        confirmLabel="Delete"
        pending={remove.isPending}
        error={remove.isError ? messageOf(remove.error) : null}
        onConfirm={confirmDelete}
        onCancel={() => {
          setToDelete(null);
          remove.reset();
        }}
      >
        {toDelete?.name} will be removed from the PC's folder.
      </ConfirmDialog>
    </section>
  );
}
