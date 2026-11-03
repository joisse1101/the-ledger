import type { BreakCountdown } from '../shared/types'

export const MS_PER_MINUTE = 60_000
/** The most one tick can add. A PC that slept for hours makes one long gap between ticks, and
 *  this keeps that gap from counting as work. */
export const MAX_TICK_MS = 5000
/** How long the work count runs before a break until the backend says otherwise (the Settings page's default). */
export const DEFAULT_BREAK_MINUTES = 60

/**
 * Counts work time toward a break. Pure: it knows no windows or files, and takes its clock as an
 * argument so a test can drive it with fake time.
 */
export class BreakTimer {
  private elapsedMs = 0
  private lastTickAt: number

  constructor(private readonly now: () => number = Date.now) {
    this.lastTickAt = now()
  }

  /** Whether the count has reached the break length given on the latest tick. */
  due = false

  /** Adds the time since the last tick (at most MAX_TICK_MS) unless AFK is on. The break length
   *  comes with every tick, so a new Settings value applies to a count in progress. */
  tick(afkOn: boolean, breakMinutes: number): void {
    const at = this.now()
    const gap = Math.max(0, at - this.lastTickAt)
    this.lastTickAt = at
    if (!afkOn) this.elapsedMs += Math.min(gap, MAX_TICK_MS)
    this.due = this.elapsedMs >= breakMinutes * MS_PER_MINUTE
  }

  /** Starts the count again from zero, as closing the break window does. */
  reset(): void {
    this.elapsedMs = 0
    this.due = false
    this.lastTickAt = this.now()
  }

  /** Work time counted so far, in milliseconds. */
  get workedMs(): number {
    return this.elapsedMs
  }

  /** Whole seconds left before a break at the given length, never below 0. Changes nothing, so
   *  the list window can read it without disturbing the count. */
  remaining(breakMinutes: number): number {
    return Math.max(0, Math.ceil((breakMinutes * MS_PER_MINUTE - this.elapsedMs) / 1000))
  }
}

/** What the list window's top bar shows: the time left, and whether it is paused by AFK. A break
 *  that is due or open shows 0:00. */
export function breakCountdown(
  timer: BreakTimer,
  afkOn: boolean,
  breakMinutes: number,
  breakOpen: boolean,
): BreakCountdown {
  const remainingSeconds = timer.due || breakOpen ? 0 : timer.remaining(breakMinutes)
  return { remainingSeconds, paused: afkOn }
}
