/** Shapes shared by the main process, the preload bridge and the renderer. Types only. */

/** The subset of `GET /api/live`'s per-session payload the widget uses. */
export interface LiveSession {
  session_id: string
  project: string
  git_branch: string
  /** `label` is built by the server (`claude_context.format_context`) and shown verbatim. */
  context: { label: string } | null
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

/** What the preload bridge exposes to the renderer as `window.widget`. */
export interface WidgetBridge {
  onState(callback: (state: LiveState) => void): void
  onCollapsed(callback: (collapsed: boolean) => void): void
  onOpacity(callback: (opacity: number) => void): void
  setOpacity(opacity: number): void
  /** The height the window needs to show its content; the main process resizes to it. */
  setContentHeight(height: number): void
  openSession(sessionId: string): Promise<OpenRepoResult>
  openLedger(): void
  toggleCollapse(): void
}
