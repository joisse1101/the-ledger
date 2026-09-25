import { useEffect, useRef, useState } from "react";
import { useDeleteProject, useMeta, useOverview } from "../../api/queries";
import type { Project, TimeRange } from "../../api/types";
import { ConfirmDialog } from "../ConfirmDialog";
import { ActivityLineChart } from "../overview/ActivityLineChart";
import { GroupBarChart } from "../overview/GroupBarChart";
import { GroupDonutChart } from "../overview/GroupDonutChart";
import { TimeRangeSelector } from "../overview/TimeRangeSelector";
import styles from "./ProjectDetailPanel.module.css";

export interface ProjectDetailPanelProps {
  project: Project;
  /** Changes each time the panel should be scrolled into view, even for the project already open.
   *  0 (the initial value) means "don't scroll", so reopening the page from a `?project=` link
   *  leaves the scroll position alone. */
  scrollKey: number;
  /** The project was deleted: the page clears its selection. */
  onDeleted: () => void;
}

/** The selected project's panel, shown under the Projects list: the Overview time range plus that
 *  project's charts grouped by git branch, and (on the machine running the app only) a "Delete
 *  project" button that opens a confirmation modal. The page renders it with `key={project.path}`,
 *  so the range starts at "All time" for every newly selected project and a fresh query never
 *  shows the previous project's charts. */
export function ProjectDetailPanel({ project, scrollKey, onDeleted }: ProjectDetailPanelProps) {
  const panelRef = useRef<HTMLElement>(null);
  const [range, setRange] = useState<TimeRange>("All time");
  const [confirming, setConfirming] = useState(false);
  const overview = useOverview(range, { project: project.path, groupBy: "branch", bucketMinutes: 60 });
  const deleteProject = useDeleteProject();
  // Deletes are local-only server-side, so no other device is even shown the button.
  const isLocal = useMeta().data?.is_local === true;
  const data = overview.data;

  // CSS `scroll-margin-top` keeps the panel's top clear of the sticky top bar.
  useEffect(() => {
    if (scrollKey === 0) return;
    panelRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }, [scrollKey]);

  const closeConfirm = () => {
    setConfirming(false);
    deleteProject.reset(); // a failure shown last time shouldn't greet the next attempt
  };

  const confirmDelete = () => {
    deleteProject.mutate(project.path, {
      onSuccess: () => {
        setConfirming(false);
        onDeleted();
      },
    });
  };

  return (
    <section ref={panelRef} className={styles.root} aria-label={`Charts for ${project.name}`}>
      <header className={styles.header}>
        <div className={styles.heading}>
          <h2 className={styles.title}>{project.name}</h2>
          <code className={styles.path}>{project.path}</code>
        </div>
        {isLocal && (
          <button type="button" className="button button-danger" onClick={() => setConfirming(true)}>
            Delete project
          </button>
        )}
      </header>

      <TimeRangeSelector value={range} onChange={setRange} />

      {data && !data.empty && (
        <>
          <GroupDonutChart groups={data.groups} groupOrder={data.group_order} groupLabel="branch" />
          <GroupBarChart groups={data.groups} groupOrder={data.group_order} groupLabel="branch" />
          <ActivityLineChart activity={data.activity} bucketMinutes={60} />
        </>
      )}

      {data?.empty && (
        <p className="muted">
          {range === "All time"
            ? "No sessions found for this project."
            : `No sessions found for ${range.toLowerCase()}.`}
        </p>
      )}

      <ConfirmDialog
        open={confirming}
        title="Delete project"
        confirmLabel={deleteProject.isPending ? "Deleting…" : "Delete"}
        pending={deleteProject.isPending}
        error={deleteProject.isError ? deleteProject.error.message : null}
        onConfirm={confirmDelete}
        onCancel={closeConfirm}
      >
        <p>
          Delete project <code>{project.path}</code> from ~/.claude.json and remove all of its on-disk session
          transcripts? This cannot be undone.
        </p>
      </ConfirmDialog>
    </section>
  );
}
