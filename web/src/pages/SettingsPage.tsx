import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useMeta, useSaveSettings, useSaveWidgetMaxProjects, useSettings } from "../api/queries";
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
  const saveWidget = useSaveWidgetMaxProjects();
  const [draft, setDraft] = useState("");
  // Null until the user types, so the field follows the saved number (including after a reload).
  const [maxProjectsDraft, setMaxProjectsDraft] = useState<string | null>(null);

  if (meta.data && !isLocal) return <Navigate to="/" replace />;
  if (!meta.data) return null;

  const folders = settings.data?.worktree_folders ?? [];
  const builtIn = folders.filter((folder) => folder.built_in);
  const userFolders = folders.filter((folder) => !folder.built_in).map((folder) => folder.path);

  function onAdd(event: FormEvent) {
    event.preventDefault();
    save.mutate([...userFolders, draft], { onSuccess: () => setDraft("") });
  }

  const maxProjects = maxProjectsDraft ?? String(settings.data?.widget.max_projects ?? "");

  function onSaveWidget(event: FormEvent) {
    event.preventDefault();
    saveWidget.mutate(Number(maxProjects), { onSuccess: () => setMaxProjectsDraft(null) });
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

      <h2>Desktop widget</h2>
      <p className={styles.hint}>
        How many projects the widget lists when you hover its Ledger button. It lists GitHub projects with the most
        open issues and pull requests first, and shows how many more there are. The widget picks the change up within
        a minute.
      </p>
      {/* noValidate: the server's reason is shown inline, like the folder form's, not the browser's balloon. */}
      <form className={styles.add} onSubmit={onSaveWidget} noValidate>
        <label htmlFor="widget-max-projects">Projects shown (1 to 10)</label>
        <div className={styles.addRow}>
          <input
            id="widget-max-projects"
            type="number"
            min={1}
            max={10}
            step={1}
            value={maxProjects}
            disabled={saveWidget.isPending || settings.isPending}
            onChange={(event) => setMaxProjectsDraft(event.target.value)}
          />
          <button type="submit" className="button" disabled={saveWidget.isPending || settings.isPending}>
            Save
          </button>
        </div>
      </form>
      {saveWidget.isError && <p role="alert">{messageOf(saveWidget.error)}</p>}
    </section>
  );
}
