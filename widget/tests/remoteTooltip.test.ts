import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AUTO_SHOW_MS,
  formatTimeLeft,
  HOVER_DELAY_MS,
  placeTooltip,
  RemoteTooltip,
} from '../src/main/remoteTooltip'
import type { RemoteQr, RemoteStatus, TooltipContent } from '../src/shared/types'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

const QR: RemoteQr = { svg: '<svg/>', displayUrl: 'https://192.168.1.20:8080' }
const NOW = Date.parse('2026-10-16T12:00:00Z')
const ready = (expiresAt: string | null = '2026-10-16T20:00:00Z'): RemoteStatus => ({ state: 'ready', expiresAt })

function setup(qr: RemoteQr | null = QR) {
  const shown: (TooltipContent | null)[] = []
  const fetchQr = vi.fn(async () => qr)
  const tooltip = new RemoteTooltip({ fetchQr, present: (content) => shown.push(content), now: () => NOW })
  const last = () => shown.at(-1)
  return { tooltip, shown, fetchQr, last }
}

const hover = async (tooltip: RemoteTooltip) => {
  tooltip.setHover(true)
  await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
}

describe('what it says', () => {
  it('shows nothing while Remote mode is off or unavailable, even when hovered', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus({ state: 'off' })
    await hover(tooltip)
    expect(last()).toBeNull()
    tooltip.onStatus({ state: 'unavailable' })
    expect(last()).toBeNull()
  })

  it.each([
    [{ state: 'starting', step: 'docker' }, 'Starting Docker...'],
    [{ state: 'starting', step: 'frontend' }, 'Starting the web interface...'],
    [{ state: 'starting', step: 'gateway' }, 'Starting the gateway...'],
    [{ state: 'starting', step: null }, 'Starting Remote mode...'],
    [{ state: 'failed', reason: 'Docker Desktop is not installed' }, 'Could not start: Docker Desktop is not installed'],
  ] as [RemoteStatus, string][])('says what %j is doing, and shows no code', async (status, text) => {
    const { tooltip, last, fetchQr } = setup()
    tooltip.onStatus(status)
    await hover(tooltip)
    expect(last()).toEqual({ kind: 'message', text })
    expect(fetchQr).not.toHaveBeenCalled()
  })

  it('shows the code, the token-free address and the time left once ready', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus(ready())
    await hover(tooltip)
    expect(last()).toEqual({ kind: 'qr', svg: '<svg/>', displayUrl: 'https://192.168.1.20:8080', timeLeft: '8h 0m left' })
  })

  it('has no time left when the expiry is unknown', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus(ready(null))
    await hover(tooltip)
    expect(last()).toMatchObject({ kind: 'qr', timeLeft: null })
  })

  it('says it is getting the code until the code arrives, and again if it is missing', async () => {
    const { tooltip, last, fetchQr } = setup(null)
    tooltip.onStatus(ready())
    await hover(tooltip)
    expect(last()).toEqual({ kind: 'message', text: 'Getting the sign-in code...' })
    tooltip.onStatus(ready()) // the next poll asks again
    expect(fetchQr).toHaveBeenCalledTimes(2)
  })

  it('fetches the code once per ready period, not on every poll', async () => {
    const { tooltip, fetchQr } = setup()
    tooltip.onStatus(ready())
    await vi.advanceTimersByTimeAsync(0)
    tooltip.onStatus(ready())
    tooltip.onStatus(ready())
    expect(fetchQr).toHaveBeenCalledTimes(1)
  })

  it('drops the code when Remote mode turns off, and a late answer does not bring it back', async () => {
    let resolve!: (qr: RemoteQr) => void
    const shown: (TooltipContent | null)[] = []
    const tooltip = new RemoteTooltip({
      fetchQr: () => new Promise<RemoteQr>((r) => (resolve = r)),
      present: (content) => shown.push(content),
      now: () => NOW,
    })
    tooltip.onStatus(ready())
    await hover(tooltip)
    tooltip.onStatus({ state: 'off' })
    resolve(QR)
    await vi.advanceTimersByTimeAsync(0)
    expect(shown.at(-1)).toBeNull()
    expect(JSON.stringify(shown.at(-1))).not.toContain('svg')
  })
})

describe('when it shows', () => {
  it('waits a moment after the pointer arrives, and hides as soon as it leaves', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus({ state: 'starting', step: 'docker' })
    tooltip.setHover(true)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS - 1)
    expect(last()).toBeNull()
    await vi.advanceTimersByTimeAsync(1)
    expect(last()).not.toBeNull()
    tooltip.setHover(false)
    expect(last()).toBeNull()
  })

  it('does not show for a pointer that passed over without resting', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus({ state: 'starting', step: 'docker' })
    tooltip.setHover(true)
    await vi.advanceTimersByTimeAsync(100)
    tooltip.setHover(false)
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(last()).toBeNull()
  })

  it('pops up by itself when a start the widget watched finishes, then hides', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus({ state: 'starting', step: 'gateway' })
    tooltip.onStatus(ready())
    await vi.advanceTimersByTimeAsync(0)
    expect(last()).toMatchObject({ kind: 'qr' })
    await vi.advanceTimersByTimeAsync(AUTO_SHOW_MS)
    expect(last()).toBeNull()
  })

  it('stays up past the auto-hide while the pointer rests on the button', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus({ state: 'starting', step: 'gateway' })
    tooltip.onStatus(ready())
    await hover(tooltip)
    await vi.advanceTimersByTimeAsync(AUTO_SHOW_MS)
    expect(last()).toMatchObject({ kind: 'qr' })
  })

  it('does not pop up for a Remote mode that was already running when the widget started', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus({ state: 'unavailable' })
    tooltip.onStatus(ready())
    await vi.advanceTimersByTimeAsync(0)
    expect(last()).toBeNull()
  })

  it('hides at once if Remote mode is turned off while it is showing', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus(ready())
    await hover(tooltip)
    tooltip.onStatus({ state: 'off' })
    expect(last()).toBeNull()
  })

  it('redraws only when the content changed', async () => {
    const { tooltip, shown } = setup()
    tooltip.onStatus(ready())
    await hover(tooltip)
    const count = shown.length
    tooltip.onStatus(ready())
    tooltip.onStatus(ready())
    expect(shown.length).toBe(count)
  })

  it('stops its timers when disposed', async () => {
    const { tooltip, last } = setup()
    tooltip.onStatus({ state: 'starting', step: 'docker' })
    tooltip.setHover(true)
    tooltip.dispose()
    await vi.advanceTimersByTimeAsync(HOVER_DELAY_MS)
    expect(last()).toBeNull()
  })
})

describe('formatTimeLeft', () => {
  it.each([
    [0, '<1m'],
    [59_000, '<1m'],
    [5 * 60_000, '5m'],
    [3 * 3_600_000 + 5 * 60_000, '3h 5m'],
    [Number.NaN, '<1m'],
  ])('%d ms is %s', (ms, text) => expect(formatTimeLeft(ms)).toBe(text))
})

describe('placeTooltip', () => {
  const work = { x: 0, y: 0, width: 1920, height: 1040 }
  const size = { width: 220, height: 280 }

  it('goes under the widget, left-aligned with it', () => {
    expect(placeTooltip({ x: 100, y: 100, width: 300, height: 120 }, size, work)).toEqual({ x: 100, y: 226 })
  })

  it('goes above when there is no room below', () => {
    expect(placeTooltip({ x: 100, y: 900, width: 300, height: 120 }, size, work)).toEqual({ x: 100, y: 614 })
  })

  it('is pulled back inside the right edge of the display', () => {
    expect(placeTooltip({ x: 1800, y: 100, width: 300, height: 120 }, size, work).x).toBe(1700)
  })

  it('stays on a secondary display whose work area does not start at the origin', () => {
    const second = { x: 1920, y: 0, width: 1280, height: 1000 }
    const placed = placeTooltip({ x: 1930, y: 20, width: 300, height: 120 }, size, second)
    expect(placed.x).toBeGreaterThanOrEqual(1920)
    expect(placed.x + size.width).toBeLessThanOrEqual(3200)
  })

  it('stays on screen when it fits neither above nor below', () => {
    const placed = placeTooltip({ x: 0, y: 100, width: 300, height: 120 }, size, { x: 0, y: 0, width: 800, height: 300 })
    expect(placed.y).toBeGreaterThanOrEqual(0)
    expect(placed.y + size.height).toBeLessThanOrEqual(300)
  })
})
