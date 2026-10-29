import { describe, expect, it } from 'vitest'
import { MESSAGE_SIZE, PROJECTS_LINE_HEIGHT, tooltipSize } from '../src/main/tooltipSize'
import type { ProjectRow } from '../src/shared/types'

const row = (name: string): ProjectRow => ({ name, source: 'GitHub', issues: 1, prs: 0 })

describe('tooltipSize', () => {
  it('sizes a message and a code as before', () => {
    expect(tooltipSize({ kind: 'message', text: 'x' })).toEqual(MESSAGE_SIZE)
    expect(tooltipSize({ kind: 'qr', svg: '', displayUrl: '', timeLeft: null })).toEqual({ width: 220, height: 290 })
  })

  it('grows the projects list by one line per project', () => {
    const one = tooltipSize({ kind: 'projects', rows: [row('a')], more: 0 })
    const three = tooltipSize({ kind: 'projects', rows: [row('a'), row('b'), row('c')], more: 0 })
    expect(three.width).toBe(one.width)
    expect(three.height - one.height).toBe(2 * PROJECTS_LINE_HEIGHT)
  })

  it('adds a line for "+N more" only when there are more', () => {
    const none = tooltipSize({ kind: 'projects', rows: [row('a')], more: 0 })
    const some = tooltipSize({ kind: 'projects', rows: [row('a')], more: 2 })
    expect(some.height - none.height).toBe(PROJECTS_LINE_HEIGHT)
  })
})
