// @vitest-environment jsdom
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '../src/renderer/app'
import { remoteTitle, summaryText, trimSparkline } from '../src/renderer/view'
import type { LiveSession, LiveState, OpenRepoResult, RemoteStatus, WidgetBridge } from '../src/shared/types'

const session = (over: Partial<LiveSession> = {}): LiveSession => ({
  session_id: 's1',
  project: 'the-ledger',
  git_branch: 'main',
  context: { label: '394k ▲ +2.1k ▁▂▃▅' },
  compact: null,
  status: 'busy',
  pending_decision: null,
  auto_approve: false,
  ...over,
})

function setup(openResult: OpenRepoResult = 'opened', autoApproveResult = true) {
  document.body.className = ''
  document.body.innerHTML = `
    <span id="summary"></span><button id="remote"></button><button id="ledger"></button><button id="collapse"></button><button id="fade"></button><button id="solid"></button>
    <main id="body"></main><footer id="note"></footer>`
  let push!: (s: LiveState) => void
  let setCollapsed!: (c: boolean) => void
  let setOpacity!: (o: number) => void
  let pushRemote!: (s: RemoteStatus) => void
  const bridge: WidgetBridge = {
    onState: (cb) => (push = cb),
    onCollapsed: (cb) => (setCollapsed = cb),
    openSession: vi.fn(async () => openResult),
    openLedger: vi.fn(),
    toggleCollapse: vi.fn(),
    onOpacity: (cb) => (setOpacity = cb),
    onRemote: (cb) => (pushRemote = cb),
    setRemote: vi.fn(),
    setAutoApprove: vi.fn(async () => autoApproveResult),
    ledgerHover: vi.fn(),
    setOpacity: vi.fn(),
    setContentHeight: vi.fn(),
  }
  mount(document, bridge)
  return { bridge, pushRemote: (s: RemoteStatus) => pushRemote(s), push: (s: LiveState) => push(s), setCollapsed: (c: boolean) => setCollapsed(c), setOpacity: (o: number) => setOpacity(o) }
}

const text = (selector: string) => document.querySelector(selector)?.textContent
beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('window height', () => {
  const rowsOf = (n: number) => Array.from({ length: n }, (_, i) => session({ session_id: `s${i}` }))

  it('reports a height whenever the list changes', () => {
    const { bridge, push } = setup()
    vi.mocked(bridge.setContentHeight).mockClear()
    push({ state: 'online', relayHookSeen: false, sessions: rowsOf(2) })
    expect(bridge.setContentHeight).toHaveBeenCalledTimes(1)
  })

  it('stops growing at ten rows', () => {
    const { bridge, push } = setup()
    // jsdom does no layout, so give every row a 30px box stacked down the list.
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(30)
    vi.spyOn(HTMLElement.prototype, 'offsetTop', 'get').mockImplementation(function (this: HTMLElement) {
      return this.classList.contains('row') ? Array.from(this.parentElement!.children).indexOf(this) * 30 : 0
    })
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function (this: HTMLElement) {
      return this.children.length * 30
    })
    push({ state: 'online', relayHookSeen: false, sessions: rowsOf(10) })
    const atTen = vi.mocked(bridge.setContentHeight).mock.lastCall![0]
    push({ state: 'online', relayHookSeen: false, sessions: rowsOf(14) })
    expect(vi.mocked(bridge.setContentHeight).mock.lastCall![0]).toBe(atTen)
    vi.restoreAllMocks()
  })
})

describe('rows', () => {
  it('shows project, branch and the server label verbatim', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session()] })
    expect(text('.name')).toBe('the-ledgermain')
    expect(text('.branch')).toBe('main')
    expect(text('.ctx')).toBe('394k ▲ +2.1k ▁▂▃▅')
  })

  it('keeps only the latest sparkline segments and leaves the rest of the label alone', () => {
    expect(trimSparkline('394k ▲ +2.1k ▁▂▃▄▅▆▇█▁▂▃▄▅▆▇█▁▂▃▄')).toBe('394k ▲ +2.1k ▆▇█▁▂▃▄▅▆▇█▁▂▃▄')
    expect(trimSparkline('394k ▲ +2.1k ▁▂▃')).toBe('394k ▲ +2.1k ▁▂▃')
    expect(trimSparkline('42k')).toBe('42k')
  })

  it('shows -- when the context is unavailable and leaves other rows alone', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ context: null }), session({ session_id: 's2', context: { label: '42k' } })] })
    const labels = [...document.querySelectorAll('.ctx')].map((n) => n.textContent)
    expect(labels).toEqual(['--', '42k'])
  })

  it('shows no percentage or limit text for any row', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session(), session({ session_id: 's2', context: null, pending_decision: { id: 'p' } })] })
    expect(document.body.textContent).not.toMatch(/%|limit|window|of \d/i)
  })
})

describe('pending row', () => {
  it('tints the row but never shows the prompt content or controls', () => {
    const { push } = setup()
    const decision = { id: 'p1', tool_name: 'Bash', tool_input: { command: 'rm -rf secret' } }
    push({ state: 'online', relayHookSeen: false, sessions: [session({ pending_decision: decision })] })
    expect(document.querySelector('.row.pending')).not.toBeNull()
    expect(document.querySelector('.badge')).toBeNull()
    expect(document.body.textContent).not.toMatch(/Bash|rm -rf|secret|pending decision/)
    expect(document.querySelectorAll('.row input, .row textarea, .row button:not(.row-open, .auto-approve)')).toHaveLength(0)
    expect(text('#summary')).toBe('1 live · 1 pending')
  })

  it('leaves the row untinted when nothing is pending', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session()] })
    expect(document.querySelector('.row.pending')).toBeNull()
  })
})

describe('status tint', () => {
  it('marks an idle session as done', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ status: 'idle' })] })
    expect(document.querySelector('.row.done')).not.toBeNull()
  })

  it.each(['running', 'waiting', 'something-else'])('marks a %s session as an error', (status) => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ status })] })
    expect(document.querySelector('.row.error')).not.toBeNull()
    expect(document.querySelector('.row.done')).toBeNull()
  })

  it.each(['busy', 'unknown', ''])('leaves a session with status %j untinted', (status) => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ status })] })
    expect(document.querySelector('.row.done, .row.error, .row.pending')).toBeNull()
  })

  it.each(['idle', 'running'])('shows a pending prompt over a %s status', (status) => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ status, pending_decision: { id: 'p' } })] })
    expect(document.querySelector('.row.pending')).not.toBeNull()
    expect(document.querySelector('.row.done, .row.error')).toBeNull()
  })
})

describe('compact dot', () => {
  const grade = (state: 'ok' | 'should' | 'needs') => ({ state, since: '2026-10-19T11:00:00+00:00' })
  const dot = () => document.querySelector('.row .compact-dot') as HTMLElement

  it.each(['ok', 'should', 'needs'] as const)('shows a filled %s dot at the left of the row', (state) => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ compact: grade(state) })] })
    expect(dot().classList.contains(`compact-${state}`)).toBe(true)
    expect(dot().classList.contains('idle')).toBe(false)
    expect(dot().textContent).toBe('')
    expect(document.querySelector('.row-open')!.firstElementChild).toBe(dot())
  })

  it('draws a hollow dot for an idle session', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ status: 'idle', compact: grade('needs') })] })
    expect(dot().classList.contains('compact-needs')).toBe(true)
    expect(dot().classList.contains('idle')).toBe(true)
  })

  it('keeps an invisible placeholder for a session with no grade', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ compact: null })] })
    expect(dot().classList.contains('compact-none')).toBe(true)
  })

  it('still opens the repo when the dot is clicked', () => {
    const { push, bridge } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ compact: grade('should') })] })
    dot().click()
    expect(bridge.openSession).toHaveBeenCalledWith('s1')
  })
})

describe('row tints and transparency', () => {
  it.each(['pending', 'done', 'error'])('lets the %s tint follow the window transparency', (tint) => {
    const css = readFileSync(resolve(__dirname, '../src/renderer/style.css'), 'utf8')
    const rule = css.split(/\r?\n/).find((line) => line.startsWith(`.row.${tint}, `))!
    expect(rule).toContain('var(--bg-alpha)')
  })
})

describe('empty and offline states', () => {
  it('says there are no live sessions', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [] })
    expect(text('.empty')).toBe('No live sessions')
    expect(document.querySelector('.row')).toBeNull()
  })

  it('shows offline with no rows, even right after rows were shown', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session()] })
    push({ state: 'offline' })
    expect(document.querySelector('.row')).toBeNull()
    expect(text('.offline')).toMatch(/offline/i)
    expect(text('#summary')).toBe('Offline')
  })

  it('recovers when the backend returns', () => {
    const { push } = setup()
    push({ state: 'offline' })
    push({ state: 'online', relayHookSeen: false, sessions: [session()] })
    expect(document.querySelectorAll('.row')).toHaveLength(1)
    expect(document.querySelector('.offline')).toBeNull()
  })
})

describe('summaryText', () => {
  it('covers each state', () => {
    expect(summaryText(null)).toBe('Connecting...')
    expect(summaryText({ state: 'online', relayHookSeen: false, sessions: [session(), session()] })).toBe('2 live')
  })
})

describe('clicks', () => {
  it('opens the clicked session', async () => {
    const { push, bridge } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ session_id: 'abc' })] })
    ;(document.querySelector('.row-open') as HTMLElement).click()
    expect(bridge.openSession).toHaveBeenCalledWith('abc')
  })

  it('shows a transient note when the session ended', async () => {
    const { push } = setup('ended')
    push({ state: 'online', relayHookSeen: false, sessions: [session()] })
    ;(document.querySelector('.row-open') as HTMLElement).click()
    await vi.advanceTimersByTimeAsync(0)
    expect(text('#note')).toBe('Session ended')
    await vi.advanceTimersByTimeAsync(3500)
    expect(text('#note')).toBe('')
  })

  it('shows a generic note on failure and keeps working', async () => {
    const { push } = setup('failed')
    push({ state: 'online', relayHookSeen: false, sessions: [session()] })
    ;(document.querySelector('.row-open') as HTMLElement).click()
    await vi.advanceTimersByTimeAsync(0)
    expect(text('#note')).toMatch(/Couldn't open/)
    expect(document.querySelectorAll('.row')).toHaveLength(1)
  })
})

describe('auto-approve button', () => {
  const hookSeen = (sessions: LiveSession[]): LiveState => ({ state: 'online', relayHookSeen: true, sessions })
  const autoButton = () => document.querySelector('.auto-approve') as HTMLButtonElement

  it('is not offered before the relay hook has been seen', () => {
    const { push } = setup()
    push({ state: 'online', relayHookSeen: false, sessions: [session({ auto_approve: true })] })
    expect(autoButton()).toBeNull()
  })

  it('sits beside the open button inside the row, never nested in it', () => {
    const { push } = setup()
    push(hookSeen([session()]))
    const row = document.querySelector('.row') as HTMLElement
    expect(autoButton().parentElement).toBe(row)
    expect(row.lastElementChild).toBe(autoButton())
    expect(document.querySelector('.row-open .auto-approve')).toBeNull()
  })

  it('shows whether auto-approve is on', () => {
    const { push } = setup()
    push(hookSeen([session({ auto_approve: true })]))
    expect(autoButton().getAttribute('aria-pressed')).toBe('true')
    expect(autoButton().title).toMatch(/is on/)
    push(hookSeen([session({ auto_approve: false })]))
    expect(autoButton().getAttribute('aria-pressed')).toBe('false')
    expect(autoButton().title).toMatch(/Turn on/)
  })

  it('asks for the opposite state and does not open the repo window', () => {
    const { push, bridge } = setup()
    push(hookSeen([session({ session_id: 'abc', auto_approve: false })]))
    autoButton().click()
    expect(bridge.setAutoApprove).toHaveBeenCalledWith('abc', true)
    expect(bridge.openSession).not.toHaveBeenCalled()

    push(hookSeen([session({ session_id: 'abc', auto_approve: true })]))
    autoButton().click()
    expect(bridge.setAutoApprove).toHaveBeenLastCalledWith('abc', false)
  })

  it('follows the next poll rather than flipping by itself', async () => {
    const { push } = setup()
    push(hookSeen([session({ auto_approve: false })]))
    autoButton().click()
    await vi.advanceTimersByTimeAsync(0)
    expect(autoButton().getAttribute('aria-pressed')).toBe('false')
  })

  it('shows a note when the backend refused', async () => {
    const { push } = setup('opened', false)
    push(hookSeen([session()]))
    autoButton().click()
    await vi.advanceTimersByTimeAsync(0)
    expect(text('#note')).toMatch(/Couldn't change auto-approve/)
  })

  it('leaves a pending row with no other controls', () => {
    const { push } = setup()
    push(hookSeen([session({ pending_decision: { id: 'p1' } })]))
    expect(document.querySelectorAll('.row button')).toHaveLength(2)
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

describe('Remote mode toggle', () => {
  const remote = () => document.getElementById('remote') as HTMLButtonElement

  it('is disabled until the backend has answered, and when it is unavailable', () => {
    const { pushRemote } = setup()
    pushRemote({ state: 'unavailable' })
    expect(remote().disabled).toBe(true)
    pushRemote({ state: 'off' })
    expect(remote().disabled).toBe(false)
  })

  it.each([
    [{ state: 'off' }, 'off', 'false'],
    [{ state: 'starting', step: 'docker' }, 'starting', 'mixed'],
    [{ state: 'ready', expiresAt: null }, 'ready', 'true'],
    [{ state: 'failed', reason: 'Docker did not start in time' }, 'failed', 'false'],
  ] as [RemoteStatus, string, string][])('shows %j without a hover', (status, state, checked) => {
    const { pushRemote } = setup()
    pushRemote(status)
    expect(remote().dataset.state).toBe(state)
    expect(remote().getAttribute('aria-checked')).toBe(checked)
  })

  it('asks for Remote mode on from off or failed', () => {
    const { bridge, pushRemote } = setup()
    pushRemote({ state: 'off' })
    remote().click()
    pushRemote({ state: 'failed', reason: 'x' })
    remote().click()
    expect(vi.mocked(bridge.setRemote).mock.calls).toEqual([[true], [true]])
  })

  it('asks for it off from starting (cancel) and from ready', () => {
    const { bridge, pushRemote } = setup()
    pushRemote({ state: 'starting', step: 'gateway' })
    remote().click()
    pushRemote({ state: 'ready', expiresAt: null })
    remote().click()
    expect(vi.mocked(bridge.setRemote).mock.calls).toEqual([[false], [false]])
  })

  it('says what a click does, including why a start failed', () => {
    expect(remoteTitle({ state: 'off' })).toMatch(/turn remote mode on/i)
    expect(remoteTitle({ state: 'starting', step: null })).toMatch(/cancel/i)
    expect(remoteTitle({ state: 'ready', expiresAt: null })).toMatch(/turn it off/i)
    expect(remoteTitle({ state: 'failed', reason: 'Docker Desktop is not installed' })).toContain('Docker Desktop is not installed')
  })

  it('tells the main process when the pointer enters and leaves the Ledger button', () => {
    const { bridge } = setup()
    const ledger = document.getElementById('ledger')!
    ledger.dispatchEvent(new MouseEvent('mouseenter'))
    ledger.dispatchEvent(new MouseEvent('mouseleave'))
    expect(vi.mocked(bridge.ledgerHover).mock.calls).toEqual([[true], [false]])
  })
})
