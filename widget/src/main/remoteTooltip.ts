/**
 * When the Remote status tooltip shows, and what it says. Pure logic with its side effects
 * injected: the controller decides, `present` draws (see tooltipWindow.ts).
 *
 * It shows while the pointer rests on the Remote button, and by itself for a few seconds when
 * Remote mode finishes starting so the code can be scanned without hovering. It says nothing
 * while Remote mode is off, and it fetches the sign-in code only while Remote mode is ready.
 */

import type { RemoteQr, RemoteStatus, RemoteStep, TooltipContent } from '../shared/types'
import type { Rect } from './state'

export const HOVER_DELAY_MS = 300
export const AUTO_SHOW_MS = 8000
const GAP = 6

export interface TooltipDeps {
  fetchQr(): Promise<RemoteQr | null>
  /** Draws this content, or hides the tooltip for null. */
  present(content: TooltipContent | null): void
  now(): number
}

const STEP_TEXT: Record<RemoteStep, string> = {
  docker: 'Starting Docker...',
  frontend: 'Starting the web interface...',
  gateway: 'Starting the gateway...',
}

export function formatTimeLeft(ms: number): string {
  const minutes = Math.floor(Math.max(0, Number.isFinite(ms) ? ms : 0) / 60_000)
  if (minutes < 1) return '<1m'
  const hours = Math.floor(minutes / 60)
  return hours ? `${hours}h ${minutes % 60}m` : `${minutes}m`
}

export class RemoteTooltip {
  private status: RemoteStatus = { state: 'unavailable' }
  private qr: RemoteQr | null = null
  private qrRequested = false
  private hovering = false
  private autoShow = false
  private hoverTimer: ReturnType<typeof setTimeout> | undefined
  private autoTimer: ReturnType<typeof setTimeout> | undefined
  private lastPresented: string | undefined

  constructor(private readonly deps: TooltipDeps) {}

  /** The latest Remote status from the poller. */
  onStatus(next: RemoteStatus): void {
    const previous = this.status
    this.status = next
    if (next.state !== 'ready') {
      this.qr = null
      this.qrRequested = false
    }
    // Only a start the widget watched finish pops up; opening the widget on a running one doesn't.
    if (previous.state === 'starting' && next.state === 'ready') this.startAutoShow()
    if (next.state === 'off' || next.state === 'unavailable' || next.state === 'failed') this.stopAutoShow()
    if (next.state === 'ready' && !this.qr && !this.qrRequested) this.requestQr()
    this.refresh()
  }

  /** The pointer entered or left the Remote button. */
  setHover(hovering: boolean): void {
    clearTimeout(this.hoverTimer)
    if (hovering) {
      this.hoverTimer = setTimeout(() => {
        this.hovering = true
        this.refresh()
      }, HOVER_DELAY_MS)
      return
    }
    this.hovering = false
    this.refresh()
  }

  dispose(): void {
    clearTimeout(this.hoverTimer)
    clearTimeout(this.autoTimer)
  }

  private startAutoShow(): void {
    clearTimeout(this.autoTimer)
    this.autoShow = true
    this.autoTimer = setTimeout(() => {
      this.autoShow = false
      this.refresh()
    }, AUTO_SHOW_MS)
  }

  private stopAutoShow(): void {
    clearTimeout(this.autoTimer)
    this.autoShow = false
  }

  private requestQr(): void {
    this.qrRequested = true
    void this.deps.fetchQr().then((qr) => {
      // A stale answer (Remote mode turned off or restarted meanwhile) is dropped.
      if (this.status.state !== 'ready') return
      this.qr = qr
      this.qrRequested = qr !== null // a missing code is asked for again on the next status
      this.refresh()
    })
  }

  private content(): TooltipContent | null {
    const { status } = this
    switch (status.state) {
      case 'off':
      case 'unavailable':
        return null
      case 'starting':
        return { kind: 'message', text: status.step ? STEP_TEXT[status.step] : 'Starting Remote mode...' }
      case 'failed':
        return { kind: 'message', text: `Could not start: ${status.reason}` }
      case 'ready': {
        if (!this.qr) return { kind: 'message', text: 'Getting the sign-in code...' }
        const expiresAt = status.expiresAt ? Date.parse(status.expiresAt) : NaN
        const timeLeft = Number.isNaN(expiresAt) ? null : `${formatTimeLeft(expiresAt - this.deps.now())} left`
        return { kind: 'qr', svg: this.qr.svg, displayUrl: this.qr.displayUrl, timeLeft }
      }
    }
  }

  private refresh(): void {
    const content = this.hovering || this.autoShow ? this.content() : null
    // Called on every poll; redraw only when what is shown actually changed.
    const key = JSON.stringify(content)
    if (key === this.lastPresented) return
    this.lastPresented = key
    this.deps.present(content)
  }
}

/** Where to put a tooltip of `size` next to the `anchor` window: under it if it fits, else above,
 *  left-aligned with it, and never outside the display's work area. */
export function placeTooltip(
  anchor: Rect,
  size: { width: number; height: number },
  workArea: Rect,
): { x: number; y: number } {
  const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max))
  const x = clamp(anchor.x, workArea.x, workArea.x + workArea.width - size.width)
  const below = anchor.y + anchor.height + GAP
  const above = anchor.y - GAP - size.height
  const fitsBelow = below + size.height <= workArea.y + workArea.height
  const y = fitsBelow || above < workArea.y ? below : above
  return { x, y: clamp(y, workArea.y, workArea.y + workArea.height - size.height) }
}
