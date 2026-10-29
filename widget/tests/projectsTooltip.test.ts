import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { loadProjects, ProjectsTooltip, type ProjectsData } from '../src/main/projectsTooltip'
import { HOVER_DELAY_MS } from '../src/main/remoteTooltip'
import type { ProjectRepo, TooltipContent } from '../src/shared/types'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

const repo = (path: string, issues: number | null, prs: number | null, host: string | null = 'GitHub'): ProjectRepo => ({
  path,
  host,
  issues,
  prs,
})
const data = (repos: ProjectRepo[] | null, max = 5): ProjectsData => ({ repos, max })

function setup() {
  const shown: (TooltipContent | null)[] = []
  const refresh = vi.fn()
  const tooltip = new ProjectsTooltip({ present: (content) => shown.push(content), refresh })
  const hover = async () => {
    tooltip.setHover(true)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
  }
  return { tooltip, shown, refresh, hover, last: () => shown.at(-1) }
}

describe('what it says', () => {
  it('lists the GitHub projects as rows once hovered', async () => {
    const { tooltip, hover, last } = setup()
    tooltip.onData(data([repo('/r/app', 7, 2), repo('/r/other', 1, 0, 'gitlab.com')]))
    await hover()
    expect(last()).toEqual({
      kind: 'projects',
      rows: [{ name: 'app', source: 'GitHub', issues: 7, prs: 2 }],
      more: 0,
    })
  })

  it('cuts to the number it was told and counts the rest', async () => {
    const { tooltip, hover, last } = setup()
    tooltip.onData(data([repo('/r/a', 3, 0), repo('/r/b', 2, 0), repo('/r/c', 1, 0)], 2))
    await hover()
    expect(last()).toMatchObject({ kind: 'projects', more: 1 })
    expect((last() as { rows: unknown[] }).rows).toHaveLength(2)
  })

  it('says it is loading before the first read has finished', async () => {
    const { hover, last } = setup()
    await hover()
    expect(last()).toEqual({ kind: 'message', text: 'Loading projects...' })
  })

  it('says it could not load when the first read failed', async () => {
    const { tooltip, hover, last } = setup()
    tooltip.onData(data(null))
    await hover()
    expect(last()).toEqual({ kind: 'message', text: 'Could not load the projects' })
  })

  it('says there are no GitHub projects', async () => {
    const { tooltip, hover, last } = setup()
    tooltip.onData(data([repo('/r/none', null, null, null)]))
    await hover()
    expect(last()).toEqual({ kind: 'message', text: 'No GitHub projects' })
  })

  it('keeps the last rows when a later read fails', async () => {
    const { tooltip, hover, last } = setup()
    tooltip.onData(data([repo('/r/app', 7, 2)]))
    await hover()
    tooltip.onData(data(null))
    expect(last()).toMatchObject({ kind: 'projects', rows: [{ name: 'app' }] })
  })

  it('recovers from a failed first read when a later one succeeds', async () => {
    const { tooltip, hover, last } = setup()
    tooltip.onData(data(null))
    await hover()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    expect(last()).toMatchObject({ kind: 'projects' })
  })
})

describe('when it shows', () => {
  it('waits a moment after the pointer arrives, and hides as soon as it leaves', async () => {
    const { tooltip, last } = setup()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    tooltip.setHover(true)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS - 1)
    expect(last()).toBeUndefined()
    await vi.advanceTimersByTimeAsync(1)
    expect(last()).not.toBeNull()
    tooltip.setHover(false)
    expect(last()).toBeNull()
  })

  it('does not show for a pointer that passed over without resting, and asks for no read', async () => {
    const { tooltip, last, refresh } = setup()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    tooltip.setHover(true)
    await vi.advanceTimersByTimeAsync(100)
    tooltip.setHover(false)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(last()).toBeUndefined()
    expect(refresh).not.toHaveBeenCalled()
  })

  it('shows the rows it has at once and asks for a fresh read on each hover', async () => {
    const { tooltip, hover, refresh, last } = setup()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    await hover()
    expect(last()).toMatchObject({ kind: 'projects' })
    expect(refresh).toHaveBeenCalledTimes(1)
    tooltip.setHover(false)
    await hover()
    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('replaces the rows in place when newer ones arrive while it is open', async () => {
    const { tooltip, hover, last, shown } = setup()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    await hover()
    tooltip.onData(data([repo('/r/app', 9, 1)]))
    expect(last()).toMatchObject({ rows: [{ name: 'app', issues: 9, prs: 1 }] })
    expect(shown.filter((content) => content === null)).toHaveLength(0)
  })

  it('draws nothing when data arrives while the pointer is away', () => {
    const { tooltip, shown } = setup()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    expect(shown).toEqual([])
  })

  it('redraws only when the content changed', async () => {
    const { tooltip, hover, shown } = setup()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    await hover()
    const count = shown.length
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    expect(shown.length).toBe(count)
  })

  it('stops its timer when disposed', async () => {
    const { tooltip, last, refresh } = setup()
    tooltip.onData(data([repo('/r/app', 1, 1)]))
    tooltip.setHover(true)
    tooltip.dispose()
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(last()).toBeUndefined()
    expect(refresh).not.toHaveBeenCalled()
  })
})

describe('loadProjects', () => {
  it('reads the repo info and the number together', async () => {
    const repos = [repo('/r/app', 1, 1)]
    const api = { fetchProjectRepos: vi.fn(async () => repos), fetchMaxProjects: vi.fn(async () => 3) }
    expect(await loadProjects(api)).toEqual({ repos, max: 3 })
  })

  it('carries a failed repo read as null', async () => {
    const api = { fetchProjectRepos: vi.fn(async () => null), fetchMaxProjects: vi.fn(async () => 5) }
    expect(await loadProjects(api)).toEqual({ repos: null, max: 5 })
  })
})
