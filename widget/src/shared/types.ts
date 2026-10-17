/** Shapes shared by the main process, the preload bridge and the renderer. Types only. */

/** The subset of `GET /api/live`'s per-session payload the widget uses. */
export interface LiveSession {
  session_id: string
  project: string
  git_branch: string
  /** `label` is built by the server (`claude_context.format_context`) and shown verbatim. */
  context: { label: string } | null
  /** The session registry's state: `busy` while running, `idle` once the turn has finished. */
  status: string
  /** Only its presence matters; the widget never reads or shows the prompt itself. */
  pending_decision: unknown | null
}

export type LiveState =
  | { state: 'online'; sessions: LiveSession[] }
  | { state: 'offline' }

export type OpenRepoResult = 'opened' | 'ended' | 'failed'

export type RemoteStep = 'docker' | 'frontend' | 'gateway'

/** The backend's Remote mode as the widget needs it. `unavailable` means the backend cannot be
 *  reached or answered something unreadable, so the toggle has nothing to act on. */
export type RemoteStatus =
  | { state: 'unavailable' }
  | { state: 'off' }
  | { state: 'starting'; step: RemoteStep | null }
  | { state: 'ready'; expiresAt: string | null }
  | { state: 'failed'; reason: string }

/** The sign-in code for another device. It holds the access token, so it lives only in the main
 *  process and the tooltip: never stored, never logged. */
export interface RemoteQr {
  /** An SVG on an opaque white square. */
  svg: string
  /** The gateway's address without the token. */
  displayUrl: string
}

/** What the Remote status tooltip window draws. Built in the main process; the page only renders it. */
export type TooltipContent =
  | { kind: 'message'; text: string }
  | { kind: 'qr'; svg: string; displayUrl: string; timeLeft: string | null }

/** What the tooltip window's preload exposes to its page as `window.tooltip`. */
export interface TooltipBridge {
  onContent(callback: (content: TooltipContent) => void): void
}

/** What the preload bridge exposes to the renderer as `window.widget`. */
export interface WidgetBridge {
  onState(callback: (state: LiveState) => void): void
  onCollapsed(callback: (collapsed: boolean) => void): void
  onOpacity(callback: (opacity: number) => void): void
  setOpacity(opacity: number): void
  /** The height the window needs to show its content; the main process resizes to it. */
  setContentHeight(height: number): void
  onRemote(callback: (status: RemoteStatus) => void): void
  /** Asks the backend to turn Remote mode on or off; the new state arrives through `onRemote`. */
  setRemote(enabled: boolean): void
  /** The pointer entered or left the Ledger button, which shows the Remote status tooltip. */
  ledgerHover(hovering: boolean): void
  openSession(sessionId: string): Promise<OpenRepoResult>
  openLedger(): void
  toggleCollapse(): void
}
