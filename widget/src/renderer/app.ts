import type { LiveState, WidgetBridge } from '../shared/types'
import { renderBody, summaryText } from './view.js'

const NOTE_MS = 3000

/** Wires the page to the preload bridge. `doc` must contain #summary, #body, #note, #ledger, #collapse. */
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
  byId('ledger').addEventListener('click', () => bridge.openLedger())
  byId('collapse').addEventListener('click', () => bridge.toggleCollapse())
  render()
}
