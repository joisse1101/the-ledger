import { describe, expect, it } from 'vitest'
import { BreakController, toBreakWorkout, type BreakWindowHandle } from '../src/main/breakController'
import type { BreakState } from '../src/shared/types'
import type { Workout, WorkoutScan } from '../src/main/workouts'

const video = (name: string): Workout => ({
  id: `starter/${name}.mp4`,
  name,
  root: 'starter',
  kind: 'video',
  file: `${name}.mp4`,
})
const images: Workout = {
  id: 'mine/Neck roll',
  name: 'Neck roll',
  root: 'mine',
  kind: 'images',
  images: [
    { file: 'Neck roll/b 1.svg', seconds: 10 },
    { file: 'Neck roll/a.svg', seconds: 30 },
  ],
}

/** Stands in for the Electron windows: the always-open list window plus whatever the controller opens. */
class FakeWindows {
  open = new Set<string>(['list'])
  allClosedFired = 0
  opened = 0
  states: BreakState[] = []
  closedCalls = 0
  private onClosed: (() => void) | undefined

  remove(id: string): void {
    this.open.delete(id)
    if (this.open.size === 0) this.allClosedFired += 1
  }

  /** The user (or the system) closes the break window itself. */
  closeBreakBySystem(): void {
    this.remove('break')
    this.onClosed?.()
  }

  openWindow = (onClosed: () => void): BreakWindowHandle => {
    this.opened += 1
    this.open.add('break')
    this.onClosed = onClosed
    return { send: (state) => this.states.push(state), destroy: () => this.remove('break') }
  }
}

function setup(workouts: Workout[], randoms: number[] = [0]) {
  const windows = new FakeWindows()
  const queue = [...randoms]
  const scan = (): WorkoutScan => ({ workouts, notes: ['mine/bad: broken'] })
  const controller = new BreakController({
    scan,
    openWindow: windows.openWindow,
    onClosed: () => (windows.closedCalls += 1),
    random: () => queue.shift() ?? 0,
  })
  const last = (): BreakState => windows.states[windows.states.length - 1]
  return { controller, windows, last }
}

describe('toBreakWorkout', () => {
  it('turns files into encoded workout-scheme URLs', () => {
    expect(toBreakWorkout(images)).toEqual({
      kind: 'images',
      name: 'Neck roll',
      images: [
        { src: 'ledger-workout://mine/Neck%20roll/b%201.svg', seconds: 10 },
        { src: 'ledger-workout://mine/Neck%20roll/a.svg', seconds: 30 },
      ],
    })
    expect(toBreakWorkout(video('Shrug'))).toEqual({
      kind: 'video',
      name: 'Shrug',
      src: 'ledger-workout://starter/Shrug.mp4',
    })
  })
})

describe('BreakController', () => {
  it('opens idle on one workout with the notes, and plays nothing', () => {
    const { controller, windows, last } = setup([video('A'), video('B')])
    expect(controller.open()).toBe(true)
    expect(windows.opened).toBe(1)
    expect(last()).toMatchObject({ stage: 'idle', workout: { name: 'A' }, notes: ['mine/bad: broken'] })
  })

  it('plays on Start', () => {
    const { controller, last } = setup([video('A')])
    controller.open()
    controller.start()
    expect(last().stage).toBe('playing')
  })

  it('finishes only after playing, and can be started again', () => {
    const { controller, last } = setup([video('A')])
    controller.open()
    controller.finished()
    expect(last().stage).toBe('idle')
    controller.start()
    controller.finished()
    expect(last().stage).toBe('finished')
    controller.start()
    expect(last().stage).toBe('playing')
  })

  it('stops playing on Skip and waits for Start on a different workout', () => {
    const { controller, last } = setup([video('A'), video('B'), video('C')], [0, 0])
    controller.open()
    controller.start()
    controller.skip()
    expect(last()).toMatchObject({ stage: 'idle', workout: { name: 'B' } })
  })

  it('keeps the only workout on Skip but still waits for Start', () => {
    const { controller, last } = setup([video('A')])
    controller.open()
    controller.start()
    controller.skip()
    expect(last()).toMatchObject({ stage: 'idle', workout: { name: 'A' } })
  })

  it('opens with a no-workouts state, where Start and Skip do nothing', () => {
    const { controller, windows, last } = setup([])
    controller.open()
    controller.start()
    controller.skip()
    expect(windows.states).toHaveLength(1)
    expect(last()).toMatchObject({ stage: 'idle', workout: null })
  })

  it.each([
    ['before Start', () => undefined],
    ['during play', (c: BreakController) => c.start()],
    ['after play ends', (c: BreakController) => { c.start(); c.finished() }],
  ])('closes %s, destroying the window and restarting the count once', (_label, act) => {
    const { controller, windows } = setup([video('A')])
    controller.open()
    act(controller)
    controller.close()
    expect(controller.isOpen).toBe(false)
    expect(windows.open.has('break')).toBe(false)
    expect(windows.closedCalls).toBe(1)
    controller.close()
    expect(windows.closedCalls).toBe(1)
  })

  it('restarts the count once when the system closes the window', () => {
    const { controller, windows } = setup([video('A')])
    controller.open()
    windows.closeBreakBySystem()
    expect(controller.isOpen).toBe(false)
    expect(windows.closedCalls).toBe(1)
  })

  it('ignores a break that is due while one is open, and opens again after Close', () => {
    const { controller, windows } = setup([video('A')])
    expect(controller.open()).toBe(true)
    expect(controller.open()).toBe(false)
    expect(windows.opened).toBe(1)
    controller.close()
    expect(controller.open()).toBe(true)
    expect(windows.opened).toBe(2)
  })

  it('leaves the list window open, so closing the break window never fires window-all-closed', () => {
    const { controller, windows } = setup([video('A')])
    controller.open()
    controller.close()
    expect(windows.open.has('list')).toBe(true)
    expect(windows.allClosedFired).toBe(0)
  })
})
