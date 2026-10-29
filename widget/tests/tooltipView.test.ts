// @vitest-environment jsdom
import * as fs from 'node:fs'
import * as path from 'node:path'
import { beforeEach, describe, expect, it } from 'vitest'
import { renderTooltip } from '../src/renderer/tooltipView'

let card: HTMLElement
beforeEach(() => {
  document.body.innerHTML = '<div id="card"></div>'
  card = document.getElementById('card')!
})

describe('renderTooltip', () => {
  it('shows a message as text and nothing else', () => {
    renderTooltip(card, { kind: 'message', text: 'Starting Docker...' })
    expect(card.textContent).toBe('Starting Docker...')
    expect(card.querySelector('img')).toBeNull()
  })

  it('shows the code as an image, the address and the time left', () => {
    renderTooltip(card, {
      kind: 'qr',
      svg: '<svg xmlns="http://www.w3.org/2000/svg"/>',
      displayUrl: 'https://192.168.1.20:8080',
      timeLeft: '7h 52m left',
    })
    const image = card.querySelector('img')!
    expect(image.getAttribute('src')).toMatch(/^data:image\/svg\+xml;utf8,/)
    expect(image.alt).toBe('Sign-in QR code')
    expect(card.querySelector('.address')?.textContent).toBe('https://192.168.1.20:8080')
    expect(card.querySelector('.left')?.textContent).toBe('7h 52m left')
    expect(card.textContent).not.toMatch(/token/i)
  })

  it('omits the time line when the expiry is unknown', () => {
    renderTooltip(card, { kind: 'qr', svg: '<svg/>', displayUrl: 'https://10.0.0.5:8080', timeLeft: null })
    expect(card.querySelector('.left')).toBeNull()
  })

  it('never inserts the SVG as markup, so nothing in it can run', () => {
    renderTooltip(card, {
      kind: 'qr',
      svg: '<svg onload="alert(1)"><script>alert(2)</script></svg>',
      displayUrl: 'https://10.0.0.5:8080',
      timeLeft: null,
    })
    expect(card.querySelector('svg, script')).toBeNull()
    // It only ever exists URL-encoded inside the image's data URL, where an <img> never runs it.
    expect(card.innerHTML).not.toContain('<svg')
    expect(card.querySelector('img')!.getAttribute('src')).toContain('%3Csvg')
  })

  it('replaces what was there before', () => {
    renderTooltip(card, { kind: 'qr', svg: '<svg/>', displayUrl: 'https://10.0.0.5:8080', timeLeft: '1m left' })
    renderTooltip(card, { kind: 'message', text: 'Starting the gateway...' })
    expect(card.children).toHaveLength(1)
    expect(card.querySelector('img')).toBeNull()
  })
})

describe('renderTooltip: projects', () => {
  const rows = [
    { name: 'the-ledger', source: 'GitHub', issues: 7, prs: 2 },
    { name: 'scratch', source: 'GitHub', issues: null, prs: null },
  ]

  it('shows a heading line and a line per project with name, source, issues and PRs', () => {
    renderTooltip(card, { kind: 'projects', rows, more: 0 })
    const cells = [...card.querySelectorAll('.cell')].map((cell) => cell.textContent)
    expect(cells).toEqual([
      'Project', 'Source', 'Issues', 'PRs',
      'the-ledger', 'GitHub', '7', '2',
      'scratch', 'GitHub', '--', '--',
    ])
  })

  it('shows a "+N more" line only when there are more', () => {
    renderTooltip(card, { kind: 'projects', rows, more: 3 })
    expect(card.querySelector('.more')?.textContent).toBe('+3 more')
    renderTooltip(card, { kind: 'projects', rows, more: 0 })
    expect(card.querySelector('.more')).toBeNull()
  })

  it('shows a zero count as 0, not as unavailable', () => {
    renderTooltip(card, { kind: 'projects', rows: [{ name: 'quiet', source: 'GitHub', issues: 0, prs: 0 }], more: 0 })
    expect([...card.querySelectorAll('.num')].map((cell) => cell.textContent)).toEqual(['0', '0'])
  })

  it('inserts every value as text, never as markup', () => {
    renderTooltip(card, {
      kind: 'projects',
      rows: [{ name: '<img src=x onerror=alert(1)>', source: '<b>GitHub</b>', issues: 1, prs: 1 }],
      more: 0,
    })
    expect(card.querySelector('img, b')).toBeNull()
    expect(card.querySelector('.name')?.textContent).toBe('<img src=x onerror=alert(1)>')
  })

  it('replaces a code that was there before', () => {
    renderTooltip(card, { kind: 'qr', svg: '<svg/>', displayUrl: 'https://10.0.0.5:8080', timeLeft: null })
    renderTooltip(card, { kind: 'projects', rows, more: 0 })
    expect(card.querySelector('img')).toBeNull()
    expect(card.children).toHaveLength(1)
  })
})

describe('the tooltip page', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'src', 'renderer', 'tooltip.html'), 'utf8')

  it('has a strict CSP: no remote content, scripts and styles from itself, images only as data', () => {
    const csp = html.match(/Content-Security-Policy" content="([^"]+)"/)![1]
    expect(csp).toBe("default-src 'none'; script-src 'self'; style-src 'self'; img-src data:")
  })

  it('has the card the script fills', () => {
    expect(html).toContain('id="card"')
  })
})
