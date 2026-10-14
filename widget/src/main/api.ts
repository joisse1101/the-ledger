import type { LiveSession, LiveState, OpenRepoResult } from '../shared/types'

export const POLL_TIMEOUT_MS = 3000

export interface Api {
  fetchLive(): Promise<LiveState>
  openRepo(sessionId: string): Promise<OpenRepoResult>
  /** Whether anything answers the backend's `/api/meta`. */
  backendUp(): Promise<boolean>
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
): Api {
  const base = `http://127.0.0.1:${backendPort}`
  const signal = () => AbortSignal.timeout(timeoutMs)

  return {
    async fetchLive() {
      try {
        const response = await fetchImpl(`${base}/api/live`, { signal: signal() })
        if (!response.ok) return { state: 'offline' }
        const body = (await response.json()) as { sessions?: LiveSession[] }
        if (!Array.isArray(body.sessions)) return { state: 'offline' }
        return { state: 'online', sessions: body.sessions }
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
