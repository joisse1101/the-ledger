import type { LiveState, WidgetBridge } from '../shared/types'
import { renderBody, summaryText } from './view.js'

const NOTE_MS = 3000
const OPACITY_STEP = 0.1
const MIN_OPACITY = 0.1

/** Wires the page to the preload bridge. `doc` must contain #summary, #body, #note, #ledger, #collapse, #fade, #solid. */
export function mount(doc: Document, bridge: WidgetBridge): void {
  const byId = (id: string) => doc.getElementById(id) as HTMLElement
  const summary = byId('summary')
  const body = byId('body')
  const note = byId('note')
  let state: LiveState | null = null
  let noteTimer: ReturnType<typeof setTimeout> | undefined

  const showNote = (text: string) => {
    note.textContent = text
    clearTimeout(noteTimer)
    noteTimer = setTimeout(() => (note.textContent = ''), NOTE_MS)
  }

  const onOpen = async (sessionId: string) => {
    const result = await bridge.openSession(sessionId)
    if (result === 'ended') showNote('Session ended')
    else if (result === 'failed') showNote("Couldn't open the repo window")
  }

  const render = () => {
    summary.textContent = summaryText(state)
    renderBody(body, state, onOpen)
  }

  bridge.onState((next) => {
    state = next
    render()
  })
  bridge.onCollapsed((collapsed) => doc.body.classList.toggle('collapsed', collapsed))
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
  byId('ledger').addEventListener('click', () => bridge.openLedger())
  byId('collapse').addEventListener('click', () => bridge.toggleCollapse())
  render()
}
