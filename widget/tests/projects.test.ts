import { describe, expect, it } from 'vitest'
import { projectName, projectsView } from '../src/main/projects'
import type { ProjectRepo } from '../src/shared/types'

const repo = (path: string, issues: number | null, prs: number | null, host: string | null = 'GitHub'): ProjectRepo => ({
  path,
  host,
  issues,
  prs,
})

describe('projectName', () => {
  it.each([
    ['C:\\Users\\me\\repos\\the-ledger', 'the-ledger'],
    ['/home/me/repos/the-ledger', 'the-ledger'],
    ['/home/me/repos/the-ledger/', 'the-ledger'],
    ['solo', 'solo'],
    ['/', '/'],
  ])('names %s as %s', (path, name) => expect(projectName(path)).toBe(name))
})

describe('projectsView', () => {
  it('lists name, source, issues and pull requests', () => {
    expect(projectsView([repo('/r/app', 7, 2)], 5)).toEqual({
      rows: [{ name: 'app', source: 'GitHub', issues: 7, prs: 2 }],
      more: 0,
    })
  })

  it('orders by issues plus pull requests, most first', () => {
    const view = projectsView([repo('/r/a', 1, 0), repo('/r/b', 3, 4), repo('/r/c', 0, 5)], 5)
    expect(view.rows.map((row) => row.name)).toEqual(['b', 'c', 'a'])
  })

  it('keeps the backend order for ties', () => {
    const view = projectsView([repo('/r/x', 2, 1), repo('/r/y', 3, 0), repo('/r/z', 1, 2)], 5)
    expect(view.rows.map((row) => row.name)).toEqual(['x', 'y', 'z'])
  })

  it('puts projects with unreadable counts after those with counts, even a count of zero', () => {
    const view = projectsView([repo('/r/unknown', null, null), repo('/r/quiet', 0, 0), repo('/r/busy', 9, 9)], 5)
    expect(view.rows.map((row) => row.name)).toEqual(['busy', 'quiet', 'unknown'])
    expect(view.rows[2]).toMatchObject({ issues: null, prs: null })
  })

  it('cuts to the cap and counts the rest', () => {
    const repos = Array.from({ length: 7 }, (_, i) => repo(`/r/p${i}`, 7 - i, 0))
    const view = projectsView(repos, 5)
    expect(view.rows.map((row) => row.name)).toEqual(['p0', 'p1', 'p2', 'p3', 'p4'])
    expect(view.more).toBe(2)
  })

  it('leaves out projects that are not on GitHub or have no remote', () => {
    const view = projectsView(
      [repo('/r/gl', 5, 5, 'gitlab.com'), repo('/r/none', null, null, null), repo('/r/gh', 1, 1)],
      5,
    )
    expect(view.rows.map((row) => row.name)).toEqual(['gh'])
    expect(view.more).toBe(0)
  })

  it('is empty when no project is on GitHub', () => {
    expect(projectsView([repo('/r/none', null, null, null)], 5)).toEqual({ rows: [], more: 0 })
    expect(projectsView([], 5)).toEqual({ rows: [], more: 0 })
  })

  it('does not reorder the list it was given', () => {
    const repos = [repo('/r/a', 1, 0), repo('/r/b', 9, 0)]
    projectsView(repos, 5)
    expect(repos.map((r) => r.path)).toEqual(['/r/a', '/r/b'])
  })
})
