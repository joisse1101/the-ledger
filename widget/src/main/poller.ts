export const POLL_INTERVAL_MS = 2000

export interface Poller {
  /** Poll now instead of waiting for the next tick. */
  refresh(): Promise<void>
  stop(): void
}

/** Polls on a fixed delay between polls (never overlapping), pushing every result to `onState`. */
export function startPoller<T>(
  fetchLive: () => Promise<T>,
  onState: (state: T) => void,
  intervalMs = POLL_INTERVAL_MS,
): Poller {
  let timer: ReturnType<typeof setTimeout> | undefined
  let stopped = false
  let inFlight: Promise<void> | undefined

  const tick = (): Promise<void> => {
    inFlight ??= fetchLive()
      .then((state) => {
        if (!stopped) onState(state)
      })
      .finally(() => {
        inFlight = undefined
      })
    return inFlight
  }

  const loop = async () => {
    await tick()
    if (!stopped) timer = setTimeout(loop, intervalMs)
  }
  void loop()

  return {
    refresh: tick,
    stop() {
      stopped = true
      if (timer) clearTimeout(timer)
    },
  }
}
