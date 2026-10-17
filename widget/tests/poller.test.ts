import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { startPoller } from '../src/main/poller'
import type { LiveState } from '../src/shared/types'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('startPoller', () => {
  it('polls immediately, then on the interval, pushing every result', async () => {
    const results: LiveState[] = [{ state: 'online', relayHookSeen: false, sessions: [] }, { state: 'offline' }]
    const fetchLive = vi.fn(async () => results.shift() ?? { state: 'offline' as const })
    const seen: LiveState[] = []
    const poller = startPoller(fetchLive, (s) => seen.push(s), 1000)

    await vi.advanceTimersByTimeAsync(0)
    expect(seen).toEqual([{ state: 'online', relayHookSeen: false, sessions: [] }])
    await vi.advanceTimersByTimeAsync(1000)
    expect(seen.at(-1)).toEqual({ state: 'offline' })
    poller.stop()
  })

  it('never overlaps polls: refresh during a poll joins it', async () => {
    let release!: () => void
    const fetchLive = vi.fn(
      () => new Promise<LiveState>((resolve) => (release = () => resolve({ state: 'offline' }))),
    )
    const poller = startPoller(fetchLive, () => {}, 1000)
    const second = poller.refresh()
    release()
    await second
    expect(fetchLive).toHaveBeenCalledTimes(1)
    poller.stop()
  })

  it('stops polling and ignores a result that lands after stop', async () => {
    const fetchLive = vi.fn(async () => ({ state: 'offline' as const }))
    const onState = vi.fn()
    const poller = startPoller(fetchLive, onState, 1000)
    await vi.advanceTimersByTimeAsync(0)
    poller.stop()
    await vi.advanceTimersByTimeAsync(5000)
    expect(fetchLive).toHaveBeenCalledTimes(1)
  })
})
