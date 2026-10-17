import type { LiveSession, LiveState, RemoteStatus } from '../shared/types'

/** Header text: the one-line summary shown both expanded and as the collapsed pill. */
export function summaryText(state: LiveState | null): string {
  if (!state) return 'Connecting...'
  if (state.state === 'offline') return 'Offline'
  const count = state.sessions.length
  if (count === 0) return 'No live sessions'
  const pending = state.sessions.filter((s) => s.pending_decision).length
  return pending > 0 ? `${count} live · ${pending} pending` : `${count} live`
}

/** The Remote toggle's hover text: what it is now and what a click does. */
export function remoteTitle(status: RemoteStatus): string {
  switch (status.state) {
    case 'unavailable':
      return 'Remote mode (backend offline)'
    case 'off':
      return 'Turn Remote mode on'
    case 'starting':
      return 'Starting Remote mode... click to cancel'
    case 'ready':
      return 'Remote mode is on. Click to turn it off'
    case 'failed':
      return `Remote mode could not start: ${status.reason}. Click to try again`
  }
}

/** Sparkline segments kept in a row; the label's trailing glyphs are the newest responses. */
export const SPARK_SEGMENTS = 15

/** The server's context label with its trailing sparkline cut to the latest segments. */
export function trimSparkline(label: string, max = SPARK_SEGMENTS): string {
  const match = label.match(/[▁-█]+$/u)
  if (!match || match[0].length <= max) return label
  return label.slice(0, match.index) + match[0].slice(-max)
}

/** Registry statuses that mean the session is no longer running; a pending prompt takes precedence. */
const FINISHED_STATUSES: ReadonlySet<string> = new Set(['idle', 'stopped'])

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

/** The auto-approve button's hover text: what it is now and what a click does. */
export function autoApproveTitle(on: boolean): string {
  return on
    ? 'Auto-approve is on: permission prompts are approved for you. Click to turn it off'
    : "Turn on auto-approve: approve this session's permission prompts for me"
}

export interface RowActions {
  onOpen: (sessionId: string) => void
  onAutoApprove: (sessionId: string, enabled: boolean) => void
}

/** A row is a wrapper holding two sibling buttons (a button cannot nest in a button): the one that
 *  opens the repo window, which fills the row, and, once the relay hook has been seen, the
 *  auto-approve button at its right end. */
function renderRow(doc: Document, session: LiveSession, showAutoApprove: boolean, actions: RowActions): HTMLElement {
  const row = el(doc, 'div', 'row')
  row.dataset.sessionId = session.session_id
  const open = el(doc, 'button', 'row-open')
  open.type = 'button'

  const name = el(doc, 'span', 'name', session.project)
  if (session.git_branch) name.append(el(doc, 'span', 'branch', session.git_branch))

  // The server's own label (size, growth marker, sparkline); only the sparkline is shortened. `--` when unknown.
  const context = el(doc, 'span', 'ctx', trimSparkline(session.context?.label || '--'))

  open.append(name, context)
  open.addEventListener('click', () => actions.onOpen(session.session_id))
  row.append(open)
  if (showAutoApprove) {
    const auto = el(doc, 'button', 'auto-approve', 'Auto')
    auto.type = 'button'
    auto.setAttribute('aria-pressed', String(session.auto_approve))
    auto.title = autoApproveTitle(session.auto_approve)
    auto.addEventListener('click', () => actions.onAutoApprove(session.session_id, !session.auto_approve))
    row.append(auto)
  }
  if (session.pending_decision) row.classList.add('pending')
  else if (FINISHED_STATUSES.has(session.status)) row.classList.add('done')
  return row
}

/** Replaces the list area's content for the given state. Offline never shows rows. */
export function renderBody(body: HTMLElement, state: LiveState | null, actions: RowActions): void {
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
  for (const session of state.sessions) body.append(renderRow(doc, session, state.relayHookSeen, actions))
}
