import type { TooltipContent } from '../shared/types'

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

const UNAVAILABLE = '--'
const count = (value: number | null): string => (value === null ? UNAVAILABLE : String(value))

/** The projects list as one grid: a heading line, a line per project and a "+N more" line, each
 *  a fixed height so the window can be sized from the line count. Every value is set as text. */
function projectsGrid(doc: Document, content: Extract<TooltipContent, { kind: 'projects' }>): HTMLElement {
  const grid = el(doc, 'div', 'projects')
  for (const heading of ['Project', 'Source', 'Issues', 'PRs']) grid.append(el(doc, 'span', 'cell head', heading))
  for (const row of content.rows) {
    grid.append(
      el(doc, 'span', 'cell name', row.name),
      el(doc, 'span', 'cell', row.source),
      el(doc, 'span', 'cell num', count(row.issues)),
      el(doc, 'span', 'cell num', count(row.prs)),
    )
  }
  if (content.more > 0) grid.append(el(doc, 'span', 'cell more', `+${content.more} more`))
  return grid
}

/** Replaces the card's content. The code is shown as an `<img>` of a data URL, never inserted as
 *  markup, so nothing in the SVG can run; the address is text, and carries no token. */
export function renderTooltip(root: HTMLElement, content: TooltipContent): void {
  const doc = root.ownerDocument
  root.replaceChildren()
  if (content.kind === 'message') {
    root.append(el(doc, 'p', 'message', content.text))
    return
  }
  if (content.kind === 'projects') {
    root.append(projectsGrid(doc, content))
    return
  }
  const code = el(doc, 'img', 'code')
  code.alt = 'Sign-in QR code'
  code.src = `data:image/svg+xml;utf8,${encodeURIComponent(content.svg)}`
  root.append(code, el(doc, 'p', 'address', content.displayUrl))
  if (content.timeLeft) root.append(el(doc, 'p', 'left', content.timeLeft))
}
