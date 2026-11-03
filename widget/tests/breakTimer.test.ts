import { describe, expect, it } from 'vitest'
import { BREAK_MINUTES_POLL_MS, BreakTimer, DEFAULT_BREAK_MINUTES, MAX_TICK_MS, MS_PER_MINUTE } from '../src/main/breakTimer'

describe('break length poll', () => {
  it('reads the break length every 30 seconds', () => {
    expect(BREAK_MINUTES_POLL_MS).toBe(30_000)
  })
})

/** A timer on a clock the test moves by hand. */
function setup() {
  let time = 1_000_000
  const timer = new BreakTimer(() => time)
  /** Runs one-second ticks for `seconds` of fake time. */
  const run = (seconds: number, afkOn = false, breakMinutes = DEFAULT_BREAK_MINUTES) => {
    for (let i = 0; i < seconds; i += 1) {
      time += 1000
      timer.tick(afkOn, breakMinutes)
    }
  }
  const jump = (ms: number) => {
    time += ms
  }
  return { timer, run, jump }
}

describe('BreakTimer', () => {
  it('is not due before the break length and due after an hour of work', () => {
    const { timer, run } = setup()
    run(59 * 60)
    expect(timer.due).toBe(false)
    run(60)
    expect(timer.due).toBe(true)
    expect(DEFAULT_BREAK_MINUTES).toBe(60)
  })

  it('pauses while AFK is on and resumes when it goes off', () => {
    const { timer, run } = setup()
    run(10 * 60)
    run(20 * 60, true)
    expect(timer.workedMs).toBe(10 * MS_PER_MINUTE)
    run(49 * 60)
    expect(timer.due).toBe(false)
    run(60)
    expect(timer.due).toBe(true)
  })

  it('counts a 3 hour sleep gap as at most one capped tick', () => {
    const { timer, run, jump } = setup()
    run(10 * 60)
    jump(3 * 60 * MS_PER_MINUTE)
    timer.tick(false, DEFAULT_BREAK_MINUTES)
    expect(timer.workedMs).toBe(10 * MS_PER_MINUTE + MAX_TICK_MS)
    expect(timer.due).toBe(false)
  })

  it('starts from zero on reset and counts the next hour afresh', () => {
    const { timer, run } = setup()
    run(60 * 60)
    expect(timer.due).toBe(true)
    timer.reset()
    expect(timer.due).toBe(false)
    expect(timer.workedMs).toBe(0)
    run(59 * 60)
    expect(timer.due).toBe(false)
    run(60)
    expect(timer.due).toBe(true)
  })

  it('does not count the time between a reset and the next tick beyond the cap', () => {
    const { timer, jump } = setup()
    timer.reset()
    jump(2000)
    timer.tick(false, DEFAULT_BREAK_MINUTES)
    expect(timer.workedMs).toBe(2000)
  })

  it('applies a break length lowered mid-count on the next tick', () => {
    const { timer, run } = setup()
    run(30 * 60)
    expect(timer.due).toBe(false)
    run(1, false, 20)
    expect(timer.due).toBe(true)
  })

  it('reports the full break length before any work', () => {
    const { timer } = setup()
    expect(timer.remaining(60)).toBe(3600)
  })

  it('reaches 0 after an hour of work and stays there', () => {
    const { timer, run } = setup()
    run(59 * 60)
    expect(timer.remaining(60)).toBe(60)
    run(60)
    expect(timer.remaining(60)).toBe(0)
    run(30)
    expect(timer.remaining(60)).toBe(0)
  })

  it('does not change while AFK is on', () => {
    const { timer, run } = setup()
    run(18 * 60)
    expect(timer.remaining(60)).toBe(42 * 60)
    run(5 * 60, true)
    expect(timer.remaining(60)).toBe(42 * 60)
  })

  it('goes back to the full length on reset', () => {
    const { timer, run } = setup()
    run(10 * 60)
    timer.reset()
    expect(timer.remaining(60)).toBe(3600)
  })

  it('follows a break length lowered mid-count and never goes below 0', () => {
    const { timer, run } = setup()
    run(30 * 60)
    expect(timer.remaining(45)).toBe(15 * 60)
    expect(timer.remaining(20)).toBe(0)
  })

  it('does not change the count when read', () => {
    const { timer, run } = setup()
    run(10)
    timer.remaining(60)
    expect(timer.workedMs).toBe(10_000)
  })

  it('applies a break length raised mid-count', () => {
    const { timer, run } = setup()
    run(60 * 60)
    expect(timer.due).toBe(true)
    run(1, false, 120)
    expect(timer.due).toBe(false)
  })
})
