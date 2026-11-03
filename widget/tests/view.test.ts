// @vitest-environment jsdom
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'
import { mount } from '../src/renderer/app'
import { countdownText, countdownTitle } from '../src/renderer/view'
import type { BreakCountdown, WidgetBridge } from '../src/shared/types'

function setup() {
  document.body.className = ''
  document.body.innerHTML = `
    <span id="summary"></span><span class="actions"><span id="countdown"></span><button id="afk"></button></span>
    <button id="remote"></button><button id="ledger"></button><button id="collapse"></button><button id="fade"></button><button id="solid"></button>
    <main id="body"></main><footer id="note"></footer>`
  let push!: (c: BreakCountdown) => void
  let setCollapsed!: (c: boolean) => void
  const bridge: WidgetBridge = {
    onState: vi.fn(),
    onCollapsed: (cb) => (setCollapsed = cb),
    onOpacity: vi.fn(),
    onRemote: vi.fn(),
    onAfk: vi.fn(),
    onBreakCountdown: (cb) => (push = cb),
    setAfk: vi.fn(async () => true),
    setRemote: vi.fn(),
    setAutoApprove: vi.fn(async () => true),
    ledgerHover: vi.fn(),
    remoteHover: vi.fn(),
    setOpacity: vi.fn(),
    setContentHeight: vi.fn(),
    openSession: vi.fn(async () => 'opened' as const),
    openLedger: vi.fn(),
    toggleCollapse: vi.fn(),
  }
  mount(document, bridge)
  return { push: (c: BreakCountdown) => push(c), setCollapsed: (c: boolean) => setCollapsed(c) }
}

const countdown = () => document.getElementById('countdown') as HTMLElement

describe('countdown text', () => {
  it.each([
    [3600, '60:00'],
    [42 * 60 + 10, '42:10'],
    [59, '0:59'],
    [5, '0:05'],
    [0, '0:00'],
  ])('writes %i seconds as %s', (seconds, text) => {
    expect(countdownText(seconds)).toBe(text)
  })
})

describe('countdown tooltip', () => {
  it('spells out the minutes and seconds', () => {
    expect(countdownTitle({ remainingSeconds: 42 * 60 + 10, paused: false })).toBe('Next break in 42 min 10 s')
  })

  it('says it is paused while AFK is on', () => {
    expect(countdownTitle({ remainingSeconds: 42 * 60 + 10, paused: true })).toBe('Next break in 42 min 10 s (paused, AFK on)')
  })
})

describe('countdown element', () => {
  it('shows m:ss and the tooltip from each push', () => {
    const { push } = setup()
    push({ remainingSeconds: 42 * 60 + 10, paused: false })
    expect(countdown().textContent).toBe('42:10')
    expect(countdown().title).toBe('Next break in 42 min 10 s')
    expect(countdown().dataset.state).toBeUndefined()
  })

  it('looks paused while AFK is on and normal again after', () => {
    const { push } = setup()
    push({ remainingSeconds: 100, paused: true })
    expect(countdown().dataset.state).toBe('paused')
    expect(countdown().title).toContain('(paused, AFK on)')
    push({ remainingSeconds: 99, paused: false })
    expect(countdown().dataset.state).toBeUndefined()
  })

  it('shows 0:00 when a break is due or open', () => {
    const { push } = setup()
    push({ remainingSeconds: 0, paused: false })
    expect(countdown().textContent).toBe('0:00')
  })

  it('keeps updating while collapsed so the time is right on expanding', () => {
    const { push, setCollapsed } = setup()
    setCollapsed(true)
    push({ remainingSeconds: 61, paused: false })
    setCollapsed(false)
    expect(countdown().textContent).toBe('1:01')
  })

  it('is the first child of the actions in the page and hidden in the pill by the stylesheet', () => {
    const html = readFileSync(resolve(__dirname, '../src/renderer/index.html'), 'utf8')
    document.body.innerHTML = html.slice(html.indexOf('<header'), html.indexOf('</header>'))
    expect(document.querySelector('.actions')!.firstElementChild!.id).toBe('countdown')
    const css = readFileSync(resolve(__dirname, '../src/renderer/style.css'), 'utf8')
    expect(css).toMatch(/body\.collapsed #countdown/)
  })
})
