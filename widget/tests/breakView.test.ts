// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createBreakView, type BreakActions } from '../src/renderer/breakView'
import type { BreakState } from '../src/shared/types'

let root: HTMLElement
let actions: { [K in keyof BreakActions]: ReturnType<typeof vi.fn> }
const view = () => createBreakView(root, actions)

const images: BreakState['workout'] = {
  kind: 'images',
  name: 'Neck roll',
  images: [
    { src: 'ledger-workout://mine/n/b.svg', seconds: 10 },
    { src: 'ledger-workout://mine/n/a.svg', seconds: 30 },
  ],
}

beforeEach(() => {
  vi.useFakeTimers()
  document.body.innerHTML = '<main id="break"></main>'
  root = document.getElementById('break')!
  actions = { start: vi.fn(), skip: vi.fn(), close: vi.fn(), finished: vi.fn() }
})
afterEach(() => vi.useRealTimers())

const press = (label: string) =>
  [...root.querySelectorAll('button')].find((b) => b.textContent === label)!.click()
const labels = () => [...root.querySelectorAll('button')].map((b) => b.textContent)

describe('createBreakView', () => {
  it('waits for Start: shows the name and nothing playing', () => {
    view().render({ workout: images, stage: 'idle', notes: [] })
    expect(root.querySelector('.title')?.textContent).toBe('Neck roll')
    expect(labels()).toEqual(['Close', 'Skip', 'Start'])
    expect(root.querySelector('img')).toBeNull()
    expect(root.querySelector('video')).toBeNull()
  })

  it('sends the button presses', () => {
    view().render({ workout: images, stage: 'idle', notes: [] })
    press('Start')
    press('Skip')
    press('Close')
    expect([actions.start, actions.skip, actions.close].map((a) => a.mock.calls.length)).toEqual([1, 1, 1])
  })

  it('steps through the images in order for their seconds, then reports the end', () => {
    view().render({ workout: images, stage: 'playing', notes: [] })
    const picture = root.querySelector('img')!
    expect(picture.getAttribute('src')).toBe('ledger-workout://mine/n/b.svg')
    vi.advanceTimersByTime(9_999)
    expect(picture.getAttribute('src')).toBe('ledger-workout://mine/n/b.svg')
    vi.advanceTimersByTime(1)
    expect(picture.getAttribute('src')).toBe('ledger-workout://mine/n/a.svg')
    expect(actions.finished).not.toHaveBeenCalled()
    vi.advanceTimersByTime(30_000)
    expect(actions.finished).toHaveBeenCalledTimes(1)
  })

  it('stops stepping when a new state replaces the playing one', () => {
    const v = view()
    v.render({ workout: images, stage: 'playing', notes: [] })
    v.render({ workout: images, stage: 'idle', notes: [] })
    vi.advanceTimersByTime(60_000)
    expect(actions.finished).not.toHaveBeenCalled()
  })

  it('plays a video and shows a note when it cannot be played, keeping Skip and Close', () => {
    view().render({
      workout: { kind: 'video', name: 'Shrug', src: 'ledger-workout://starter/Shrug.mp4' },
      stage: 'playing',
      notes: [],
    })
    const player = root.querySelector('video')!
    expect(player.getAttribute('src')).toBe('ledger-workout://starter/Shrug.mp4')
    player.dispatchEvent(new Event('error'))
    expect(root.querySelector('video')).toBeNull()
    expect(root.querySelector('.note')?.textContent).toContain('cannot be played')
    expect(labels()).toEqual(['Close', 'Skip'])
  })

  it('reports the end of a video', () => {
    view().render({
      workout: { kind: 'video', name: 'Shrug', src: 'ledger-workout://starter/Shrug.mp4' },
      stage: 'playing',
      notes: [],
    })
    root.querySelector('video')!.dispatchEvent(new Event('ended'))
    expect(actions.finished).toHaveBeenCalledTimes(1)
  })

  it('offers only Close, with a note, when there are no workouts', () => {
    view().render({ workout: null, stage: 'idle', notes: ['mine/bad: broken'] })
    expect(labels()).toEqual(['Close'])
    expect(root.querySelector('.note')?.textContent).toContain('no workouts')
    expect(root.querySelector('.problems')?.textContent).toContain('mine/bad: broken')
  })

  it('offers Play again once finished', () => {
    view().render({ workout: images, stage: 'finished', notes: [] })
    expect(labels()).toEqual(['Close', 'Skip', 'Play again'])
  })

  it('sets a workout name as text, never as markup', () => {
    view().render({ workout: { ...images, name: '<img src=x>' } as BreakState['workout'], stage: 'idle', notes: [] })
    expect(root.querySelector('.title')?.textContent).toBe('<img src=x>')
    expect(root.querySelector('img')).toBeNull()
  })
})
