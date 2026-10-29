import type {
  LiveSession,
  LiveState,
  OpenRepoResult,
  ProjectRepo,
  RemoteQr,
  RemoteStatus,
  RemoteStep,
} from '../shared/types'

export const POLL_TIMEOUT_MS = 3000
/** Turning Remote mode off runs `docker compose down` inside the request, so it gets longer. */
export const REMOTE_SWITCH_TIMEOUT_MS = 20_000
/** The repo read runs `git` and `gh` for every project when the backend's cache is cold, so it
 *  gets longer than a poll. The poller never overlaps reads, so waiting costs nothing. */
export const REPOS_TIMEOUT_MS = 30_000
/** How many projects the tooltip lists until the backend says otherwise (the Settings page's default). */
export const DEFAULT_MAX_PROJECTS = 5

export interface Api {
  fetchLive(): Promise<LiveState>
  openRepo(sessionId: string): Promise<OpenRepoResult>
  /** Whether anything answers the backend's `/api/meta`. */
  backendUp(): Promise<boolean>
  /** Remote mode as `/api/meta` reports it. */
  fetchRemote(): Promise<RemoteStatus>
  /** Turns Remote mode on or off and returns the state the backend answered with. */
  setRemoteMode(enabled: boolean): Promise<RemoteStatus>
  /** The sign-in code while Remote mode is ready, else null. */
  fetchQr(): Promise<RemoteQr | null>
  /** Switches one session's auto-approve; false when the backend refused or did not answer. */
  setAutoApprove(sessionId: string, enabled: boolean): Promise<boolean>
  /** Every known project's repo info, or null when the backend did not answer or answered something unreadable. */
  fetchProjectRepos(): Promise<ProjectRepo[] | null>
  /** How many projects the tooltip lists, as the Settings page has it; the default when it cannot be read. */
  fetchMaxProjects(): Promise<number>
}

const STEPS: readonly string[] = ['docker', 'frontend', 'gateway']

/** Reads the backend's `remote_mode` object; anything unexpected is `unavailable`, never a guess. */
export function toRemoteStatus(remoteMode: unknown): RemoteStatus {
  if (typeof remoteMode !== 'object' || remoteMode === null) return { state: 'unavailable' }
  const { state, step, reason, expires_at: expiresAt } = remoteMode as Record<string, unknown>
  switch (state) {
    case 'off':
      return { state: 'off' }
    case 'starting':
      return { state: 'starting', step: typeof step === 'string' && STEPS.includes(step) ? (step as RemoteStep) : null }
    case 'ready':
      return { state: 'ready', expiresAt: typeof expiresAt === 'string' ? expiresAt : null }
    case 'failed':
      return { state: 'failed', reason: typeof reason === 'string' && reason ? reason : 'Remote mode could not start' }
    default:
      return { state: 'unavailable' }
  }
}

const nullableString = (value: unknown): string | null => (typeof value === 'string' ? value : null)
const nullableCount = (value: unknown): number | null =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : null

/** One entry of `/api/projects/repos`; null for anything without a path, so one bad entry never hides the rest. */
function toProjectRepo(entry: unknown): ProjectRepo | null {
  if (typeof entry !== 'object' || entry === null) return null
  const { path, host, issues, prs } = entry as Record<string, unknown>
  if (typeof path !== 'string' || !path) return null
  return { path, host: nullableString(host), issues: nullableCount(issues), prs: nullableCount(prs) }
}

type FetchLike = typeof fetch

/**
 * The loopback client for the backend. Requests go to 127.0.0.1, whose Host header the backend
 * treats as local, so no token is needed (and none is stored); the renderer never calls this.
 */
export function createApi(
  backendPort: number,
  fetchImpl: FetchLike = fetch,
  timeoutMs = POLL_TIMEOUT_MS,
  reposTimeoutMs = REPOS_TIMEOUT_MS,
): Api {
  const base = `http://127.0.0.1:${backendPort}`
  const signal = () => AbortSignal.timeout(timeoutMs)

  /** Whether `/api/meta` says a prompt has been relayed. Anything unreadable counts as not seen:
   *  the auto-approve button stays hidden rather than appear on a guess. */
  const relayHookSeen = async (): Promise<boolean> => {
    try {
      const response = await fetchImpl(`${base}/api/meta`, { signal: signal() })
      if (!response.ok) return false
      return ((await response.json()) as { relay_hook_seen?: unknown }).relay_hook_seen === true
    } catch {
      return false
    }
  }

  return {
    async fetchLive() {
      try {
        const response = await fetchImpl(`${base}/api/live`, { signal: signal() })
        if (!response.ok) return { state: 'offline' }
        const body = (await response.json()) as { sessions?: LiveSession[] }
        if (!Array.isArray(body.sessions)) return { state: 'offline' }
        return { state: 'online', sessions: body.sessions, relayHookSeen: await relayHookSeen() }
      } catch {
        return { state: 'offline' }
      }
    },

    async openRepo(sessionId) {
      try {
        const response = await fetchImpl(
          `${base}/api/sessions/${encodeURIComponent(sessionId)}/open-repo`,
          { method: 'POST', headers: { 'X-Requested-With': 'ledger' }, signal: signal() },
        )
        if (response.ok) return 'opened'
        return response.status === 404 ? 'ended' : 'failed'
      } catch {
        return 'failed'
      }
    },

    async fetchRemote() {
      try {
        const response = await fetchImpl(`${base}/api/meta`, { signal: signal() })
        if (!response.ok) return { state: 'unavailable' }
        return toRemoteStatus(((await response.json()) as { remote_mode?: unknown }).remote_mode)
      } catch {
        return { state: 'unavailable' }
      }
    },

    async setRemoteMode(enabled) {
      try {
        const response = await fetchImpl(`${base}/api/remote-mode`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'ledger', 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled }),
          signal: AbortSignal.timeout(REMOTE_SWITCH_TIMEOUT_MS),
        })
        if (!response.ok) return { state: 'unavailable' }
        return toRemoteStatus(await response.json())
      } catch {
        return { state: 'unavailable' }
      }
    },

    async fetchQr() {
      try {
        const response = await fetchImpl(`${base}/api/remote-mode/qr`, { signal: signal() })
        if (!response.ok) return null
        const body = (await response.json()) as { svg?: unknown; display_url?: unknown }
        if (typeof body.svg !== 'string' || typeof body.display_url !== 'string') return null
        return { svg: body.svg, displayUrl: body.display_url }
      } catch {
        return null
      }
    },

    async setAutoApprove(sessionId, enabled) {
      try {
        const response = await fetchImpl(`${base}/api/sessions/${encodeURIComponent(sessionId)}/auto-approve`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'ledger', 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled }),
          signal: signal(),
        })
        return response.ok
      } catch {
        return false
      }
    },

    async fetchProjectRepos() {
      try {
        const response = await fetchImpl(`${base}/api/projects/repos`, { signal: AbortSignal.timeout(reposTimeoutMs) })
        if (!response.ok) return null
        const { repos } = (await response.json()) as { repos?: unknown }
        if (!Array.isArray(repos)) return null
        return repos.flatMap((entry) => toProjectRepo(entry) ?? [])
      } catch {
        return null
      }
    },

    async fetchMaxProjects() {
      try {
        const response = await fetchImpl(`${base}/api/settings`, { signal: signal() })
        if (!response.ok) return DEFAULT_MAX_PROJECTS
        const { widget } = (await response.json()) as { widget?: { max_projects?: unknown } }
        const value = widget?.max_projects
        return typeof value === 'number' && Number.isInteger(value) && value >= 1 ? value : DEFAULT_MAX_PROJECTS
      } catch {
        return DEFAULT_MAX_PROJECTS
      }
    },

    async backendUp() {
      try {
        const response = await fetchImpl(`${base}/api/meta`, { signal: signal() })
        return response.ok
      } catch {
        return false
      }
    },
  }
}
