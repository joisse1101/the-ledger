import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useProjects } from "../api/queries";
import type { Project } from "../api/types";
import { ProjectDetailPanel } from "../components/projects/ProjectDetailPanel";
import { ProjectsList } from "../components/projects/ProjectsList";

// The selected project lives in the URL (?project=<path>) rather than component state, so a reload
// or shared link reopens the same project's charts.
export function ProjectsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const path = searchParams.get("project");
  // Bumped on every selection (including the project already open) to scroll the panel into view.
  const [scrollKey, setScrollKey] = useState(0);
  const projects = useProjects();
  const selected = path ? (projects.data?.projects.find((p) => p.path === path) ?? null) : null;

  const select = useCallback(
    (project: Project) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("project", project.path);
        return next;
      });
      setScrollKey((key) => key + 1);
    },
    [setSearchParams],
  );

  const clear = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete("project");
        return next;
      },
      { replace: true },
    );
  }, [setSearchParams]);

  // A ?project= that isn't a known project (deleted, or a stale link) is dropped rather than
  // shown as an error. Only once the list has loaded, or every reload would lose its selection.
  const loaded = projects.data !== undefined;
  useEffect(() => {
    if (loaded && path && !selected) clear();
  }, [loaded, path, selected, clear]);

  return (
    <section>
      <h1>Projects</h1>
      <ProjectsList selectedPath={selected?.path ?? null} onSelect={select} />
      {selected && (
        <ProjectDetailPanel key={selected.path} project={selected} scrollKey={scrollKey} onDeleted={clear} />
      )}
    </section>
  );
}
