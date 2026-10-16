import * as fs from 'node:fs'
import * as path from 'node:path'
import { describe, expect, it } from 'vitest'
import { CHANNELS } from '../src/shared/ipc'

describe('preload channels', () => {
  it('uses exactly the channel names in shared/ipc.ts', () => {
    const preloads = ['index.ts', 'tooltip.ts'].map((file) =>
      fs.readFileSync(path.join(__dirname, '..', 'src', 'preload', file), 'utf8'),
    )
    const used = preloads.flatMap((source) => [...source.matchAll(/'(widget:[a-z-]+)'/g)].map((m) => m[1]))
    expect(new Set(used)).toEqual(new Set(Object.values(CHANNELS)))
  })
})
