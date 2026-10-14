// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '../src/renderer/app'
import { summaryText } from '../src/renderer/view'
import type { LiveSession, LiveState, OpenRepoResult, WidgetBridge } from '../src/shared/types'

const session = (over: Partial<LiveSession> = {}): LiveSession => ({
  session_id: 's1',
  project: 'the-ledger',
  git_branch: 'main',
  context: { label: '394k ▲ +2.1k ▁▂▃▅' },
  pending_decision: null,
  ...over,
})

function setup(openResult: OpenRepoResult = 'opened') {
  document.body.className = ''
  document.body.innerHTML = `
    <span id="summary"></span><button id="ledger"></button><button id="collapse"></button><button id="fade"></button><button id="solid"></button>
    <main id="body"></main><footer id="note"></footer>`
  let push!: (s: LiveState) => void
  let setCollapsed!: (c: boolean) => void
  let setOpacity!: (o: number) => void
  const bridge: WidgetBridge = {
    onState: (cb) => (push = cb),
    onCollapsed: (cb) => (setCollapsed = cb),
    openSession: vi.fn(async () => openResult),
    openLedger: vi.fn(),
    toggleCollapse: vi.fn(),
    onOpacity: (cb) => (setOpacity = cb),
    setOpacity: vi.fn(),
  }
  mount(document, bridge)
  return { bridge, push: (s: LiveState) => push(s), setCollapsed: (c: boolean) => setCollapsed(c), setOpacity: (o: number) => setOpacity(o) }
}

const text = (selector: string) => document.querySelector(selector)?.textContent
beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('rows', () => {
  it('shows project, branch and the server label verbatim', () => {
    const { push } = setup()
    push({ state: 'online', sessions: [session()] })
    expect(text('.name')).toBe('the-ledgermain')
    expect(text('.branch')).toBe('main')
    expect(text('.ctx')).toBe('394k ▲ +2.1k ▁▂▃▅')
  })

  it('shows -- when the context is unavailable and leaves other rows alone', () => {
    const { push } = setup()
    push({ state: 'online', sessions: [session({ context: null }), session({ session_id: 's2', context: { label: '42k' } })] })
    const labels = [...document.querySelectorAll('.ctx')].map((n) => n.textContent)
    expect(labels).toEqual(['--', '42k'])
  })

  it('shows no percentage or limit text for any row', () => {
    const { push } = setup()
    push({ state: 'online', sessions: [session(), session({ session_id: 's2', context: null, pending_decision: { id: 'p' } })] })
    expect(document.body.textContent).not.toMatch(/%|limit|window|of \d/i)
  })
})

describe('pending badge', () => {
  it('shows the badge but never the prompt content or controls', () => {
    const { push } = setup()
    const decision = { id: 'p1', tool_name: 'Bash', tool_input: { command: 'rm -rf secret' } }
    push({ state: 'online', sessions: [session({ pending_decision: decision })] })
    expect(text('.badge')).toBe('pending')
    expect(document.body.textContent).not.toMatch(/Bash|rm -rf|secret/)
    expect(document.querySelectorAll('button.row button, .row input, .row textarea')).toHaveLength(0)
    expect(text('#summary')).toBe('1 live · 1 pending')
  })

  it('has no badge when nothing is pending', () => {
    const { push } = setup()
    push({ state: 'online', sessions: [session()] })
    expect(document.querySelector('.badge')).toBeNull()
  })
})

describe('empty and offline states', () => {
  it('says there are no live sessions', () => {
    const { push } = setup()
    push({ state: 'online', sessions: [] })
    expect(text('.empty')).toBe('No live sessions')
    expect(document.querySelector('.row')).toBeNull()
  })

  it('shows offline with no rows, even right after rows were shown', () => {
    const { push } = setup()
    push({ state: 'online', sessions: [session()] })
    push({ state: 'offline' })
    expect(document.querySelector('.row')).toBeNull()
    expect(text('.offline')).toMatch(/offline/i)
    expect(text('#summary')).toBe('Offline')
  })

  it('recovers when the backend returns', () => {
    const { push } = setup()
    push({ state: 'offline' })
    push({ state: 'online', sessions: [session()] })
    expect(document.querySelectorAll('.row')).toHaveLength(1)
    expect(document.querySelector('.offline')).toBeNull()
  })
})

describe('summaryText', () => {
  it('covers each state', () => {
    expect(summaryText(null)).toBe('Connecting...')
    expect(summaryText({ state: 'online', sessions: [session(), session()] })).toBe('2 live')
  })
})

describe('clicks', () => {
  it('opens the clicked session', async () => {
    const { push, bridge } = setup()
    push({ state: 'online', sessions: [session({ session_id: 'abc' })] })
    ;(document.querySelector('.row') as HTMLElement).click()
    expect(bridge.openSession).toHaveBeenCalledWith('abc')
  })

  it('shows a transient note when the session ended', async () => {
    const { push } = setup('ended')
    push({ state: 'online', sessions: [session()] })
    ;(document.querySelector('.row') as HTMLElement).click()
    await vi.advanceTimersByTimeAsync(0)
    expect(text('#note')).toBe('Session ended')
    await vi.advanceTimersByTimeAsync(3500)
    expect(text('#note')).toBe('')
  })

  it('shows a generic note on failure and keeps working', async () => {
    const { push } = setup('failed')
    push({ state: 'online', sessions: [session()] })
    ;(document.querySelector('.row') as HTMLElement).click()
    await vi.advanceTimersByTimeAsync(0)
    expect(text('#note')).toMatch(/Couldn't open/)
    expect(document.querySelectorAll('.row')).toHaveLength(1)
  })
})

describe('toolbar', () => {
  it('forwards Ledger and collapse clicks and mirrors the collapsed state', () => {
    const { bridge, setCollapsed } = setup()
    ;(document.getElementById('ledger') as HTMLElement).click()
    ;(document.getElementById('collapse') as HTMLElement).click()
    expect(bridge.openLedger).toHaveBeenCalled()
    expect(bridge.toggleCollapse).toHaveBeenCalled()
    setCollapsed(true)
    expect(document.body.classList.contains('collapsed')).toBe(true)
    setCollapsed(false)
    expect(document.body.classList.contains('collapsed')).toBe(false)
  })
})

describe('opacity', () => {
  const alpha = () => document.documentElement.style.getPropertyValue('--bg-alpha')
  const click = (id: string) => document.getElementById(id)!.click()

  it('applies the saved opacity to the background', () => {
    const { setOpacity } = setup()
    setOpacity(0.4)
    expect(alpha()).toBe('0.4')
  })

  it('steps down and up with the small and big sun, telling the main process', () => {
    const { bridge, setOpacity } = setup()
    setOpacity(0.5)
    click('fade')
    expect(alpha()).toBe('0.4')
    expect(bridge.setOpacity).toHaveBeenLastCalledWith(0.4)
    click('solid')
    click('solid')
    expect(bridge.setOpacity).toHaveBeenLastCalledWith(0.6)
  })

  it('stays between 10% and 100%', () => {
    const { setOpacity } = setup()
    setOpacity(0.1)
    click('fade')
    expect(alpha()).toBe('0.1')
    setOpacity(1)
    click('solid')
    expect(alpha()).toBe('1')
  })
})
