import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  afkMinutesLeft,
  chimeFolder,
  CHIME_SCRIPT,
  clearAfk,
  isChimeInstalled,
  pollLiveAndAfk,
  readAfk,
  switchAfk,
  writeAfk,
} from '../src/main/afk'
import type { LiveState } from '../src/shared/types'

const NOW = Date.parse('2026-11-02T10:00:00.000Z')
const MINUTE = 60_000

let folder: string
beforeEach(() => {
  folder = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-afk-'))
})
afterEach(() => {
  fs.rmSync(folder, { recursive: true })
})

const flagFile = () => path.join(folder, 'state', 'afk.flag')
const putFlag = (text: string) => {
  fs.mkdirSync(path.dirname(flagFile()), { recursive: true })
  fs.writeFileSync(flagFile(), text)
}
const install = () => fs.writeFileSync(path.join(folder, CHIME_SCRIPT), '# mock')

describe('chimeFolder', () => {
  it('is the folder the installer uses under the home folder', () => {
    expect(chimeFolder('home')).toBe(path.join('home', '.claude', 'hooks', 'chimeScripts'))
  })
})

describe('readAfk', () => {
  it('is on with the minutes left when the flag is in the future', () => {
    install()
    putFlag(new Date(NOW + 20 * MINUTE).toISOString())
    expect(readAfk(folder, NOW)).toEqual({ installed: true, on: true, minutesLeft: 20 })
  })

  it('rounds the minutes left up', () => {
    putFlag(new Date(NOW + 20 * MINUTE + 1000).toISOString())
    expect(afkMinutesLeft(folder, NOW)).toBe(21)
  })

  it('is off when there is no flag file', () => {
    install()
    expect(readAfk(folder, NOW)).toEqual({ installed: true, on: false, minutesLeft: 0 })
  })

  it('is off when the flag has expired', () => {
    install()
    putFlag(new Date(NOW - MINUTE).toISOString())
    expect(readAfk(folder, NOW).on).toBe(false)
  })

  it('is off when the flag is exactly due', () => {
    putFlag(new Date(NOW).toISOString())
    expect(afkMinutesLeft(folder, NOW)).toBeNull()
  })

  it.each([['garbage'], [''], ['2099-13-45T99:00:00Z']])('is off when the file holds %j', (text) => {
    putFlag(text)
    expect(afkMinutesLeft(folder, NOW)).toBeNull()
  })

  it('is off when the time has no Z suffix, since the hook reads it as UTC', () => {
    putFlag('2099-01-01T00:00:00')
    expect(afkMinutesLeft(folder, NOW)).toBeNull()
  })

  it('is off when the flag path is a folder and cannot be read', () => {
    fs.mkdirSync(flagFile(), { recursive: true })
    expect(afkMinutesLeft(folder, NOW)).toBeNull()
  })

  it('reports not installed when the chime script is missing', () => {
    expect(readAfk(folder, NOW).installed).toBe(false)
    expect(isChimeInstalled(folder)).toBe(false)
  })

  it('reports installed when the chime script is there', () => {
    install()
    expect(isChimeInstalled(folder)).toBe(true)
  })
})

describe('writeAfk', () => {
  it('writes an expiry equal to now plus the duration, as a Z-suffixed UTC time', () => {
    writeAfk(folder, 30, NOW)
    expect(fs.readFileSync(flagFile(), 'utf8')).toBe('2026-11-02T10:30:00.000Z')
  })

  it('reads back as on with the duration left', () => {
    writeAfk(folder, 10, NOW)
    expect(afkMinutesLeft(folder, NOW)).toBe(10)
  })

  it('replaces an earlier flag', () => {
    writeAfk(folder, 10, NOW)
    writeAfk(folder, 40, NOW)
    expect(afkMinutesLeft(folder, NOW)).toBe(40)
  })
})

describe('clearAfk', () => {
  it('turns an on flag off', () => {
    writeAfk(folder, 10, NOW)
    clearAfk(folder)
    expect(fs.existsSync(flagFile())).toBe(false)
  })

  it('is harmless when there is no flag', () => {
    expect(() => clearAfk(folder)).not.toThrow()
  })
})

describe('pollLiveAndAfk', () => {
  it('carries the flag while the backend is unreachable', async () => {
    install()
    writeAfk(folder, 15, NOW)
    const result = await pollLiveAndAfk(async () => ({ state: 'offline' }), folder, () => NOW)
    expect(result).toEqual({
      live: { state: 'offline' },
      afk: { installed: true, on: true, minutesLeft: 15 },
    })
  })

  it('carries the flag next to a live answer', async () => {
    const live: LiveState = { state: 'online', sessions: [], relayHookSeen: false }
    const result = await pollLiveAndAfk(async () => live, folder, () => NOW)
    expect(result.live).toBe(live)
    expect(result.afk).toEqual({ installed: false, on: false, minutesLeft: 0 })
  })
})

describe('switchAfk', () => {
  it('writes the flag for the duration it was given when switching on', async () => {
    expect(await switchAfk(folder, true, async () => 10, () => NOW)).toBe(true)
    expect(afkMinutesLeft(folder, NOW)).toBe(10)
  })

  it('clears the flag without asking for a duration when switching off', async () => {
    writeAfk(folder, 10, NOW)
    const fetchMinutes = vi.fn(async () => 99)
    expect(await switchAfk(folder, false, fetchMinutes, () => NOW)).toBe(true)
    expect(afkMinutesLeft(folder, NOW)).toBeNull()
    expect(fetchMinutes).not.toHaveBeenCalled()
  })

  it('resolves false when the flag cannot be written', async () => {
    fs.writeFileSync(path.join(folder, 'state'), 'a file where the folder should be')
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(await switchAfk(folder, true, async () => 10, () => NOW)).toBe(false)
    vi.restoreAllMocks()
  })
})
