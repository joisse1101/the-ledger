import { describe, expect, it } from 'vitest'
import { pickWorkout } from '../src/main/pickWorkout'

const pool = [{ id: 'a' }, { id: 'b' }, { id: 'c' }]

describe('pickWorkout', () => {
  it('gives different workouts for different random values', () => {
    expect(pickWorkout(pool, null, () => 0)).toEqual({ id: 'a' })
    expect(pickWorkout(pool, null, () => 0.5)).toEqual({ id: 'b' })
    expect(pickWorkout(pool, null, () => 0.99)).toEqual({ id: 'c' })
  })

  it('can reach every workout when nothing was shown before', () => {
    const seen = new Set([0, 0.4, 0.8].map((value) => pickWorkout(pool, null, () => value)?.id))
    expect(seen).toEqual(new Set(['a', 'b', 'c']))
  })

  it('never returns the current workout on Skip when several exist', () => {
    for (const value of [0, 0.3, 0.5, 0.7, 0.99]) {
      expect(pickWorkout(pool, pool[1], () => value)).not.toEqual(pool[1])
    }
  })

  it('keeps the only workout when the pool has one', () => {
    expect(pickWorkout([pool[0]], pool[0], () => 0.5)).toEqual(pool[0])
  })

  it('is null for an empty pool', () => {
    expect(pickWorkout([], null, () => 0.5)).toBeNull()
  })

  it('stays in range when random returns exactly 1', () => {
    expect(pickWorkout(pool, null, () => 1)).toEqual({ id: 'c' })
  })
})
