import { useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useProjects } from "../api/queries";
import type { Project } from "../api/types";
import { ProjectDetailPanel } from "../components/projects/ProjectDetailPanel";
import { ProjectsList } from "../components/projects/ProjectsList";

// Which projects' panels are open lives in the URL (repeated ?project=<path> params) rather than
// component state, so a reload or shared link reopens the same ones. Each panel renders inline
// beneath its own row in the list, and any number can be open at once.
export function ProjectsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const openPaths = searchParams.getAll("project");
  const projects = useProjects();
  const known = projects.data?.projects ?? [];
  const knownPaths = new Set(known.map((p) => p.path));
  const expandedPaths = new Set(openPaths.filter((p) => knownPaths.has(p)));

  const setOpenPaths = useCallback(
    (paths: string[], options?: { replace?: boolean }) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.delete("project");
        for (const p of paths) next.append("project", p);
        return next;
      }, options);
    },
    [setSearchParams],
  );

  const toggle = useCallback(
    (project: Project) => {
      setOpenPaths(
        openPaths.includes(project.path)
          ? openPaths.filter((p) => p !== project.path)
          : [...openPaths, project.path],
      );
    },
    [openPaths, setOpenPaths],
  );

  const close = useCallback(
    (path: string) => setOpenPaths(openPaths.filter((p) => p !== path), { replace: true }),
    [openPaths, setOpenPaths],
  );

  // A ?project= that isn't a known project (deleted, or a stale link) is dropped rather than
  // shown as an error, leaving any other still-open panels alone. Only once the list has loaded,
  // or every reload would lose its selection.
  const loaded = projects.data !== undefined;
  const openKey = openPaths.join("\u0000");
  const knownKey = known.map((p) => p.path).join("\u0000");
  useEffect(() => {
    if (!loaded) return;
    const kept = openPaths.filter((p) => knownPaths.has(p));
    if (kept.length !== openPaths.length) setOpenPaths(kept, { replace: true });
    // openKey/knownKey stand in for openPaths/knownPaths, which are fresh arrays/sets every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, openKey, knownKey]);

  return (
    <section>
      <h1>Projects</h1>
      <ProjectsList
        expandedPaths={expandedPaths}
        onToggle={toggle}
        renderExpanded={(project) => <ProjectDetailPanel project={project} onDeleted={() => close(project.path)} />}
      />
    </section>
  );
}
