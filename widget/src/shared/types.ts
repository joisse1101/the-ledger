/** Shapes shared by the main process, the preload bridge and the renderer. Types only. */

/** The subset of `GET /api/live`'s per-session payload the widget uses. `LiveState` adds
 *  `relayHookSeen`, read from `/api/meta`: auto-approve is offered only once it is true. */
/** Time since the session started or was last compacted: `ok` under 45 min, `should` up to 55, `needs` beyond. */
export type CompactState = 'ok' | 'should' | 'needs'

export interface LiveSession {
  session_id: string
  project: string
  git_branch: string
  /** `label` is built by the server (`claude_context.format_context`) and shown verbatim. */
  context: { label: string } | null
  /** The server's compact grade; null when the session has no known start time. */
  compact: { state: CompactState; since: string } | null
  /** The session registry's state: `busy` while running, `idle` once the turn has finished. */
  status: string
  /** Only its presence matters; the widget never reads or shows the prompt itself. */
  pending_decision: unknown | null
  /** Whether the backend approves this session's plain permission prompts by itself. */
  auto_approve: boolean
}

export type LiveState =
  | { state: 'online'; sessions: LiveSession[]; relayHookSeen: boolean }
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

/** One project's repo info as `GET /api/projects/repos` reports it. Everything but `path` is null
 *  when unknown: no remote, a host other than GitHub, or counts that could not be read. */
export interface ProjectRepo {
  path: string
  host: string | null
  issues: number | null
  prs: number | null
}

/** One row of the projects tooltip. A count is null when it could not be read. */
export interface ProjectRow {
  name: string
  source: string
  issues: number | null
  prs: number | null
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
  /** Switches one session's auto-approve; resolves false when the backend refused or was unreachable.
   *  The new state arrives with the next poll. */
  setAutoApprove(sessionId: string, enabled: boolean): Promise<boolean>
  openSession(sessionId: string): Promise<OpenRepoResult>
  openLedger(): void
  toggleCollapse(): void
}
