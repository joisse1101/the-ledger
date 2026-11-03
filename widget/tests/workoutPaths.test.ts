import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { resolveInside } from '../src/main/workoutPaths'

let temp: string
let root: string
let outside: string

beforeEach(() => {
  temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-paths-'))
  root = path.join(temp, 'root')
  outside = path.join(temp, 'outside')
  fs.mkdirSync(path.join(root, 'sub'), { recursive: true })
  fs.mkdirSync(outside)
  fs.writeFileSync(path.join(root, 'sub', 'a.png'), 'x')
  fs.writeFileSync(path.join(outside, 'secret.png'), 'x')
})

afterEach(() => {
  fs.rmSync(temp, { recursive: true })
})

describe('resolveInside', () => {
  it('returns the real path of a normal file', () => {
    expect(resolveInside(root, 'sub/a.png')).toBe(fs.realpathSync(path.join(root, 'sub', 'a.png')))
  })

  it('rejects a parent-folder path', () => {
    expect(resolveInside(root, '../outside/secret.png')).toBeNull()
    expect(resolveInside(root, 'sub/../../outside/secret.png')).toBeNull()
  })

  it('rejects absolute paths', () => {
    expect(resolveInside(root, path.join(outside, 'secret.png'))).toBeNull()
    expect(resolveInside(root, 'C:/Users/someone/photo.png')).toBeNull()
  })

  it('rejects a link that leaves the root', () => {
    // A junction needs no privilege on Windows; on other systems it is a plain symlink.
    fs.symlinkSync(outside, path.join(root, 'link'), 'junction')
    expect(resolveInside(root, 'link/secret.png')).toBeNull()
  })

  it('rejects a missing file and an empty path', () => {
    expect(resolveInside(root, 'sub/none.png')).toBeNull()
    expect(resolveInside(root, '')).toBeNull()
  })

  it('rejects everything when the root is missing', () => {
    expect(resolveInside(path.join(temp, 'nope'), 'a.png')).toBeNull()
  })
})
