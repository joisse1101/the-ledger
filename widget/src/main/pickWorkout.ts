/**
 * Picks one workout from `pool` with `random` (a function returning a number from 0 up to but
 * not including 1, like `Math.random`). When more than one workout exists, `previous` is left
 * out, so Skip always changes the workout; a pool of one keeps it. Null for an empty pool.
 */
export function pickWorkout<T extends { id: string }>(
  pool: readonly T[],
  previous: T | null,
  random: () => number = Math.random,
): T | null {
  const candidates = pool.length > 1 && previous !== null ? pool.filter((w) => w.id !== previous.id) : pool
  if (candidates.length === 0) return null
  const index = Math.min(Math.floor(random() * candidates.length), candidates.length - 1)
  return candidates[index]
}
