import type { BreakState, BreakWorkout } from '../shared/types'
import { pickWorkout } from './pickWorkout'
import { WORKOUT_SCHEME } from './workoutProtocol'
import type { Workout, WorkoutScan } from './workouts'

/** What the controller needs of a window: show a state, and go away. No Electron types, so tests pass a fake. */
export interface BreakWindowHandle {
  send(state: BreakState): void
  destroy(): void
}

export interface BreakControllerDeps {
  /** Reads the workout folders afresh, so an edited YAML file applies to the next break. */
  scan(): WorkoutScan
  /** Opens the window without taking focus. `onClosed` must be called if the window is closed by other means than `destroy`. */
  openWindow(onClosed: () => void): BreakWindowHandle
  /** Called once each time the break window goes away, however it was closed. */
  onClosed(): void
  random?: () => number
}

const workoutUrl = (workout: Workout, file: string): string =>
  `${WORKOUT_SCHEME}://${workout.root}/${file.split('/').map(encodeURIComponent).join('/')}`

/** The workout as the page gets it: URLs through the workout scheme, never file paths. */
export function toBreakWorkout(workout: Workout): BreakWorkout {
  if (workout.kind === 'video') return { kind: 'video', name: workout.name, src: workoutUrl(workout, workout.file) }
  return {
    kind: 'images',
    name: workout.name,
    images: workout.images.map((image) => ({ src: workoutUrl(workout, image.file), seconds: image.seconds })),
  }
}

/**
 * The break window's state in the main process: the chosen workout and whether it is idle,
 * playing or finished. At most one window exists; a break due while one is open is ignored, so
 * closing it is what restarts the work count. Knows nothing of Electron.
 */
export class BreakController {
  private handle: BreakWindowHandle | undefined
  private pool: Workout[] = []
  private notes: string[] = []
  private current: Workout | null = null
  private stage: BreakState['stage'] = 'idle'

  constructor(private readonly deps: BreakControllerDeps) {}

  get isOpen(): boolean {
    return this.handle !== undefined
  }

  /** Opens the break window on a randomly picked workout. False, and nothing changes, when one is already open. */
  open(): boolean {
    if (this.handle) return false
    const scan = this.deps.scan()
    this.pool = scan.workouts
    this.notes = scan.notes
    this.current = pickWorkout(this.pool, null, this.deps.random)
    this.stage = 'idle'
    this.handle = this.deps.openWindow(() => this.windowClosed())
    this.push()
    return true
  }

  /** Starts the workout, or plays a finished one again. Ignored while playing or with no workout. */
  start(): void {
    if (!this.handle || !this.current || this.stage === 'playing') return
    this.stage = 'playing'
    this.push()
  }

  /** Picks a different workout (the same one when it is the only one) and waits for Start, even mid-play. */
  skip(): void {
    if (!this.handle || !this.current) return
    this.current = pickWorkout(this.pool, this.current, this.deps.random)
    this.stage = 'idle'
    this.push()
  }

  /** The page reports the video ended or the last image's time ran out. */
  finished(): void {
    if (!this.handle || this.stage !== 'playing') return
    this.stage = 'finished'
    this.push()
  }

  /** Closes the window from any state. */
  close(): void {
    const handle = this.handle
    if (!handle) return
    this.handle = undefined
    handle.destroy()
    this.deps.onClosed()
  }

  private windowClosed(): void {
    if (!this.handle) return
    this.handle = undefined
    this.deps.onClosed()
  }

  private push(): void {
    this.handle?.send({
      workout: this.current ? toBreakWorkout(this.current) : null,
      stage: this.stage,
      notes: this.notes,
    })
  }
}
