import { describe, expect, it } from 'vitest'
import { TooltipSlot } from '../src/main/tooltipSlot'
import type { TooltipContent } from '../src/shared/types'

const qr: TooltipContent = { kind: 'qr', svg: '<svg/>', displayUrl: 'https://10.0.0.5:8080', timeLeft: null }
const projects: TooltipContent = { kind: 'projects', rows: [], more: 0 }

function setup() {
  const drawn: (TooltipContent | null)[] = []
  const slot = new TooltipSlot((content) => drawn.push(content))
  return { slot, last: () => drawn.at(-1) }
}

describe('TooltipSlot', () => {
  it('draws what a source presents, and hides when it has nothing', () => {
    const { slot, last } = setup()
    slot.present('projects', projects)
    expect(last()).toBe(projects)
    slot.present('projects', null)
    expect(last()).toBeNull()
  })

  it('draws the most recently presented content when both sources have some', () => {
    const { slot, last } = setup()
    slot.present('projects', projects)
    slot.present('remote', qr)
    expect(last()).toBe(qr)
  })

  it('keeps the other source showing when one stops, as when Remote auto-shows over a hover', () => {
    const { slot, last } = setup()
    slot.present('projects', projects)
    slot.present('remote', qr)
    slot.present('remote', null)
    expect(last()).toBe(projects)
  })

  it('hides only when neither source has content', () => {
    const { slot, last } = setup()
    slot.present('projects', projects)
    slot.present('remote', qr)
    slot.present('projects', null)
    expect(last()).toBe(qr)
    slot.present('remote', null)
    expect(last()).toBeNull()
  })

  it('moves a source to the front when it presents again', () => {
    const { slot, last } = setup()
    slot.present('remote', qr)
    slot.present('projects', projects)
    slot.present('remote', { ...qr, timeLeft: '1m left' })
    expect(last()).toMatchObject({ kind: 'qr', timeLeft: '1m left' })
  })
})
