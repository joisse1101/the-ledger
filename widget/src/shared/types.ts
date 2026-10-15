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
