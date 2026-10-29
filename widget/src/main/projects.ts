/** What the projects tooltip lists, from the backend's repo info. Pure: no I/O. */

import type { ProjectRepo, ProjectRow } from '../shared/types'

const GITHUB = 'GitHub'

export interface ProjectsView {
  rows: ProjectRow[]
  /** How many GitHub projects did not fit under the cap. */
  more: number
}

/** The folder's own name: the last segment of the path, on either kind of separator. */
export function projectName(path: string): string {
  const segments = path.split(/[\\/]/).filter(Boolean)
  return segments.at(-1) ?? path
}

/** Counts that could not be read for either kind (the backend sets both or neither). */
const isUnavailable = (repo: ProjectRepo): boolean => repo.issues === null && repo.prs === null

const openTotal = (repo: ProjectRepo): number => (repo.issues ?? 0) + (repo.prs ?? 0)

/** The GitHub projects with the most open issues plus pull requests first, those with unreadable
 *  counts after them, ties kept in the backend's order, cut to `max` rows. */
export function projectsView(repos: readonly ProjectRepo[], max: number): ProjectsView {
  const ordered = repos
    .filter((repo) => repo.host === GITHUB)
    .sort((a, b) => Number(isUnavailable(a)) - Number(isUnavailable(b)) || openTotal(b) - openTotal(a))
  const rows = ordered.slice(0, Math.max(0, max)).map(
    (repo): ProjectRow => ({ name: projectName(repo.path), source: GITHUB, issues: repo.issues, prs: repo.prs }),
  )
  return { rows, more: ordered.length - rows.length }
}
