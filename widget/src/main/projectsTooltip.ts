/**
 * What the Ledger button's tooltip says, and when. Pure logic with its side effects injected, like
 * RemoteTooltip: the controller decides, `present` draws.
 *
 * It keeps the last repo info it was given, so a hover shows rows at once and never waits on `gh`.
 * Each hover also asks for a fresh read, and rows that arrive while the tooltip is open replace
 * the shown ones in place.
 */

import type { ProjectRepo, TooltipContent } from '../shared/types'
import type { Api } from './api'
import { projectsView } from './projects'
import { HOVER_DELAY_MS } from './remoteTooltip'

/** The backend caches repo info for minutes (a failed read for one), so reading more often costs little. */
export const PROJECTS_POLL_MS = 60_000

export interface ProjectsData {
  /** Null when the backend did not answer. */
  repos: ProjectRepo[] | null
  max: number
}

/** One read of everything the tooltip needs. Neither call rejects: each falls back on its own. */
export async function loadProjects(api: Pick<Api, 'fetchProjectRepos' | 'fetchMaxProjects'>): Promise<ProjectsData> {
  const [repos, max] = await Promise.all([api.fetchProjectRepos(), api.fetchMaxProjects()])
  return { repos, max }
}

export interface ProjectsTooltipDeps {
  /** Draws this content, or hides the tooltip for null. */
  present(content: TooltipContent | null): void
  /** Starts a read now. The answer comes back through `onData`. */
  refresh(): void
}

export class ProjectsTooltip {
  private known: { repos: ProjectRepo[]; max: number } | null = null
  private loadFailed = false
  private hovering = false
  private hoverTimer: ReturnType<typeof setTimeout> | undefined
  // What the window shows now, as `redraw` keys it. It starts hidden, so nothing is drawn until there is something to show.
  private lastPresented = JSON.stringify(null)

  constructor(private readonly deps: ProjectsTooltipDeps) {}

  /** The result of a read. A failed one keeps the last good rows. */
  onData(data: ProjectsData): void {
    if (data.repos) {
      this.known = { repos: data.repos, max: data.max }
      this.loadFailed = false
    } else if (!this.known) {
      this.loadFailed = true
    }
    this.redraw()
  }

  /** The pointer entered or left the Ledger button. */
  setHover(hovering: boolean): void {
    clearTimeout(this.hoverTimer)
    if (hovering) {
      this.hoverTimer = setTimeout(() => {
        this.hovering = true
        this.redraw()
        this.deps.refresh()
      }, HOVER_DELAY_MS)
      return
    }
    this.hovering = false
    this.redraw()
  }

  dispose(): void {
    clearTimeout(this.hoverTimer)
  }

  private content(): TooltipContent {
    if (!this.known) {
      return { kind: 'message', text: this.loadFailed ? 'Could not load the projects' : 'Loading projects...' }
    }
    const { rows, more } = projectsView(this.known.repos, this.known.max)
    if (rows.length === 0) return { kind: 'message', text: 'No GitHub projects' }
    return { kind: 'projects', rows, more }
  }

  private redraw(): void {
    const content = this.hovering ? this.content() : null
    // Called on every read; redraw only when what is shown actually changed.
    const key = JSON.stringify(content)
    if (key === this.lastPresented) return
    this.lastPresented = key
    this.deps.present(content)
  }
}
