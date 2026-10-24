import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useMeta, useSaveSettings, useSettings } from "../api/queries";
import styles from "./SettingsPage.module.css";

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

/** Settings for the machine running the app. Exists only for a browser on that machine - the
 *  navigation hides it elsewhere and the server refuses its requests, so any other device that
 *  opens this address is sent home. */
export function SettingsPage() {
  const meta = useMeta();
  const isLocal = meta.data?.is_local === true;
  const settings = useSettings(isLocal);
  const save = useSaveSettings();
  const [draft, setDraft] = useState("");

  if (meta.data && !isLocal) return <Navigate to="/" replace />;
  if (!meta.data) return null;

  const folders = settings.data?.worktree_folders ?? [];
  const builtIn = folders.filter((folder) => folder.built_in);
  const userFolders = folders.filter((folder) => !folder.built_in).map((folder) => folder.path);

  function onAdd(event: FormEvent) {
    event.preventDefault();
    save.mutate([...userFolders, draft], { onSuccess: () => setDraft("") });
  }

  return (
    <section>
      <h1>Settings</h1>

      <h2>Worktree folders</h2>
      <p className={styles.hint}>
        Folders inside a repo where its git worktrees live, such as <code>.trees</code>. A session started in{" "}
        <code>&lt;repo&gt;/&lt;folder&gt;/&lt;name&gt;</code> counts toward its repo instead of showing up as a
        project of its own. This applies to every repo, and takes effect at once.
      </p>

      {settings.isError && <p role="alert">Couldn't load the settings: {messageOf(settings.error)}</p>}

      <ul className={styles.list} aria-label="Worktree folders">
        {builtIn.map((folder) => (
          <li key={folder.path} className={styles.row}>
            <code className={styles.path}>{folder.path}</code>
            <span className={styles.badge}>Built in</span>
          </li>
        ))}
        {userFolders.map((path) => (
          <li key={path} className={styles.row}>
            <code className={styles.path}>{path}</code>
            <button
              type="button"
              className="button button-danger"
              disabled={save.isPending}
              aria-label={`Remove ${path}`}
              onClick={() => save.mutate(userFolders.filter((folder) => folder !== path))}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>

      <form className={styles.add} onSubmit={onAdd}>
        <label htmlFor="worktree-folder">Add a folder</label>
        <div className={styles.addRow}>
          <input
            id="worktree-folder"
            type="text"
            value={draft}
            placeholder=".trees"
            autoComplete="off"
            spellCheck={false}
            disabled={save.isPending}
            onChange={(event) => setDraft(event.target.value)}
          />
          <button type="submit" className="button" disabled={save.isPending || settings.isPending}>
            Add
          </button>
        </div>
      </form>

      {save.isPending && (
        <p role="status" className={styles.hint}>
          Saving and re-filing sessions…
        </p>
      )}
      {save.isError && <p role="alert">{messageOf(save.error)}</p>}
    </section>
  );
}
