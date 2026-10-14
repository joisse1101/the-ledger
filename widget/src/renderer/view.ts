import type { LiveSession, LiveState } from '../shared/types'

/** Header text: the one-line summary shown both expanded and as the collapsed pill. */
export function summaryText(state: LiveState | null): string {
  if (!state) return 'Connecting...'
  if (state.state === 'offline') return 'Offline'
  const count = state.sessions.length
  if (count === 0) return 'No live sessions'
  const pending = state.sessions.filter((s) => s.pending_decision).length
  return pending > 0 ? `${count} live · ${pending} pending` : `${count} live`
}

/** Sparkline segments kept in a row; the label's trailing glyphs are the newest responses. */
export const SPARK_SEGMENTS = 15

/** The server's context label with its trailing sparkline cut to the latest segments. */
export function trimSparkline(label: string, max = SPARK_SEGMENTS): string {
  const match = label.match(/[▁-█]+$/u)
  if (!match || match[0].length <= max) return label
  return label.slice(0, match.index) + match[0].slice(-max)
}

const el = <K extends keyof HTMLElementTagNameMap>(
  doc: Document,
  tag: K,
  className: string,
  text?: string,
): HTMLElementTagNameMap[K] => {
  const node = doc.createElement(tag)
  node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function renderRow(doc: Document, session: LiveSession, onOpen: (sessionId: string) => void): HTMLElement {
  const row = el(doc, 'button', 'row')
  row.type = 'button'
  row.dataset.sessionId = session.session_id

  const name = el(doc, 'span', 'name', session.project)
  if (session.git_branch) name.append(el(doc, 'span', 'branch', session.git_branch))

  // The server's own label (size, growth marker, sparkline); only the sparkline is shortened. `--` when unknown.
  const context = el(doc, 'span', 'ctx', trimSparkline(session.context?.label || '--'))

  row.append(name, context)
  if (session.pending_decision) row.classList.add('pending')
  row.addEventListener('click', () => onOpen(session.session_id))
  return row
}

/** Replaces the list area's content for the given state. Offline never shows rows. */
export function renderBody(
  body: HTMLElement,
  state: LiveState | null,
  onOpen: (sessionId: string) => void,
): void {
  const doc = body.ownerDocument
  body.replaceChildren()
  if (!state) return
  if (state.state === 'offline') {
    body.append(el(doc, 'p', 'empty offline', 'Backend is offline. Retrying...'))
    return
  }
  if (state.sessions.length === 0) {
    body.append(el(doc, 'p', 'empty', 'No live sessions'))
    return
  }
  for (const session of state.sessions) body.append(renderRow(doc, session, onOpen))
}
