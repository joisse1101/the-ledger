import * as fs from 'node:fs'
import * as path from 'node:path'
import { describe, expect, it } from 'vitest'
import { CHANNELS } from '../src/shared/ipc'

describe('preload channels', () => {
  it('uses exactly the channel names in shared/ipc.ts', () => {
    const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'preload', 'index.ts'), 'utf8')
    const used = [...source.matchAll(/'(widget:[a-z-]+)'/g)].map((m) => m[1])
    expect(new Set(used)).toEqual(new Set(Object.values(CHANNELS)))
  })
})
