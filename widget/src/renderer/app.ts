import type { LiveState, WidgetBridge } from '../shared/types'
import { afkTitle, countdownText, countdownTitle, remoteTitle, renderBody, summaryText } from './view.js'

const NOTE_MS = 3000
const OPACITY_STEP = 0.1
const MIN_OPACITY = 0.1
const MAX_ROWS = 10
const BODY_BORDER = 2 // the 1px border above and below, which offsetHeight of the children excludes

/** Wires the page to the preload bridge. `doc` must contain #summary, #body, #note, #ledger, #afk, #countdown, #remote, #collapse, #fade, #solid. */
export function mount(doc: Document, bridge: WidgetBridge): void {
  const byId = (id: string) => doc.getElementById(id) as HTMLElement
  const summary = byId('summary')
  const body = byId('body')
  const note = byId('note')
  let state: LiveState | null = null
  let noteTimer: ReturnType<typeof setTimeout> | undefined

  // The window is as tall as its header, up to MAX_ROWS rows and the note; more rows scroll.
  const reportHeight = () => {
    const bar = byId('summary').parentElement as HTMLElement
    const rows = body.children
    // Measure to the last visible row, not body.scrollHeight: the list stretches to fill the window,
    // so its scrollHeight never drops below the current height and the window could not shrink.
    const lastRow = rows[Math.min(rows.length, MAX_ROWS) - 1] as HTMLElement | undefined
    const listHeight = lastRow ? lastRow.offsetTop + lastRow.offsetHeight - body.offsetTop : 0
    bridge.setContentHeight(BODY_BORDER + bar.offsetHeight + listHeight + note.offsetHeight)
  }

  const showNote = (text: string) => {
    note.textContent = text
    reportHeight()
    clearTimeout(noteTimer)
    noteTimer = setTimeout(() => {
      note.textContent = ''
      reportHeight()
    }, NOTE_MS)
  }

  const onOpen = async (sessionId: string) => {
    const result = await bridge.openSession(sessionId)
    if (result === 'ended') showNote('Session ended')
    else if (result === 'failed') showNote("Couldn't open the repo window")
  }

  const onAutoApprove = async (sessionId: string, enabled: boolean) => {
    if (!(await bridge.setAutoApprove(sessionId, enabled))) showNote("Couldn't change auto-approve")
  }

  const render = () => {
    summary.textContent = summaryText(state)
    renderBody(body, state, { onOpen, onAutoApprove })
    reportHeight()
  }

  bridge.onState((next) => {
    state = next
    render()
  })
  bridge.onCollapsed((collapsed) => {
    doc.body.classList.toggle('collapsed', collapsed)
    reportHeight()
  })
  let opacity = 1
  const applyOpacity = (next: number) => {
    opacity = next
    doc.documentElement.style.setProperty('--bg-alpha', String(next))
  }
  const step = (delta: number) => {
    const next = Math.min(1, Math.max(MIN_OPACITY, Math.round((opacity + delta) * 100) / 100))
    applyOpacity(next)
    bridge.setOpacity(next)
  }
  bridge.onOpacity(applyOpacity)
  byId('fade').addEventListener('click', () => step(-OPACITY_STEP))
  byId('solid').addEventListener('click', () => step(OPACITY_STEP))
  // AFK: the chimes' switch. The main process reads its flag file on each poll, so the button
  // follows the file (and shows off once it expires); it is hidden unless the chime hook is installed.
  const afk = byId('afk') as HTMLButtonElement
  let afkOn = false
  bridge.onAfk((next) => {
    afkOn = next.on
    afk.hidden = !next.installed
    afk.dataset.state = next.on ? 'on' : 'off'
    afk.setAttribute('aria-checked', String(next.on))
    afk.title = afkTitle(next)
  })
  // The break countdown: the main process owns the count and pushes it each second. The page only
  // draws it; the pill hides it with CSS while the pushes carry on.
  const countdown = byId('countdown')
  bridge.onBreakCountdown((next) => {
    countdown.textContent = countdownText(next.remainingSeconds)
    countdown.title = countdownTitle(next)
    if (next.paused) countdown.dataset.state = 'paused'
    else delete countdown.dataset.state
  })
  afk.addEventListener('click', async () => {
    if (!(await bridge.setAfk(!afkOn))) showNote("Couldn't change AFK")
  })
  // Remote mode: one click turns it on (or retries after a failure), another turns it off, and
  // while it is starting a click cancels. The state comes back from the backend, not from here.
  const remote = byId('remote') as HTMLButtonElement
  let remoteOn = false
  bridge.onRemote((status) => {
    remoteOn = status.state === 'starting' || status.state === 'ready'
    remote.dataset.state = status.state
    remote.disabled = status.state === 'unavailable'
    remote.setAttribute('aria-checked', status.state === 'ready' ? 'true' : status.state === 'starting' ? 'mixed' : 'false')
    remote.title = remoteTitle(status)
  })
  remote.addEventListener('click', () => bridge.setRemote(!remoteOn))
  // Each button's hover shows its own tooltip: the Remote button's is Remote status and the sign-in
  // code (main/remoteTooltip.ts), the Ledger button's is the projects' open issues and pull requests.
  remote.addEventListener('mouseenter', () => bridge.remoteHover(true))
  remote.addEventListener('mouseleave', () => bridge.remoteHover(false))
  const ledger = byId('ledger')
  ledger.addEventListener('mouseenter', () => bridge.ledgerHover(true))
  ledger.addEventListener('mouseleave', () => bridge.ledgerHover(false))
  ledger.addEventListener('click', () => bridge.openLedger())
  byId('collapse').addEventListener('click', () => bridge.toggleCollapse())
  render()
}
