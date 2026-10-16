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

/** Replaces the card's content. The code is shown as an `<img>` of a data URL, never inserted as
 *  markup, so nothing in the SVG can run; the address is text, and carries no token. */
export function renderTooltip(root: HTMLElement, content: TooltipContent): void {
  const doc = root.ownerDocument
  root.replaceChildren()
  if (content.kind === 'message') {
    root.append(el(doc, 'p', 'message', content.text))
    return
  }
  const code = el(doc, 'img', 'code')
  code.alt = 'Sign-in QR code'
  code.src = `data:image/svg+xml;utf8,${encodeURIComponent(content.svg)}`
  root.append(code, el(doc, 'p', 'address', content.displayUrl))
  if (content.timeLeft) root.append(el(doc, 'p', 'left', content.timeLeft))
}
