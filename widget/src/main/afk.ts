import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import type { AfkState, LiveState } from '../shared/types'

/** The chime hook's script name; the AFK button is offered only while this file is installed. */
export const CHIME_SCRIPT = 'Play-ClaudeChime.ps1'
const FLAG_FILE = 'afk.flag'
const MS_PER_MINUTE = 60_000
const CHIME_FOLDER_PARTS = ['.claude', 'hooks', 'chimeScripts']

/** Where the installer puts the chime script; the hook reads `state\afk.flag` beneath it. */
export const chimeFolder = (home: string = os.homedir()): string => path.join(home, ...CHIME_FOLDER_PARTS)

const flagPath = (folder: string): string => path.join(folder, 'state', FLAG_FILE)

/** Whether `Play-ClaudeChime.ps1` is in the chime folder. */
export const isChimeInstalled = (folder: string): boolean => fs.existsSync(path.join(folder, CHIME_SCRIPT))

/** The expiry in `afk.flag`: one UTC time with a `Z` suffix, as the hook parses it. */
function readExpiry(folder: string): number | null {
  try {
    const text = fs.readFileSync(flagPath(folder), 'utf8').trim()
    if (!text.endsWith('Z')) return null
    const expiry = Date.parse(text)
    return Number.isNaN(expiry) ? null : expiry
  } catch {
    // A missing or unreadable file is "no flag", the same rule the hook applies.
    return null
  }
}

/** Minutes left on the flag, rounded up, or null when there is no valid flag (missing, garbled or past due). */
export function afkMinutesLeft(folder: string, now: number = Date.now()): number | null {
  const expiry = readExpiry(folder)
  if (expiry === null || expiry <= now) return null
  return Math.ceil((expiry - now) / MS_PER_MINUTE)
}

/** What the header needs: whether to show the button, and whether and for how long it is on. */
export function readAfk(folder: string, now: number = Date.now()): AfkState {
  const minutesLeft = afkMinutesLeft(folder, now)
  return { installed: isChimeInstalled(folder), on: minutesLeft !== null, minutesLeft: minutesLeft ?? 0 }
}

/** Switches AFK on until `now + minutes`. Throws when the file cannot be written. */
export function writeAfk(folder: string, minutes: number, now: number = Date.now()): void {
  fs.mkdirSync(path.dirname(flagPath(folder)), { recursive: true })
  fs.writeFileSync(flagPath(folder), new Date(now + minutes * MS_PER_MINUTE).toISOString(), 'ascii')
}

/** Switches AFK off. Already off is fine. */
export function clearAfk(folder: string): void {
  fs.rmSync(flagPath(folder), { force: true })
}

/** One poll: the backend's live state and the flag file, read independently so a dead backend
 *  never hides the flag. */
export async function pollLiveAndAfk(
  fetchLive: () => Promise<LiveState>,
  folder: string,
  now: () => number = Date.now,
): Promise<{ live: LiveState; afk: AfkState }> {
  const live = await fetchLive()
  return { live, afk: readAfk(folder, now()) }
}

/** Handles a press of the AFK button. Switching on asks `fetchMinutes` for the duration (which
 *  falls back by itself when the backend is down); switching off needs nothing from the backend.
 *  Resolves false when the flag file could not be changed. */
export async function switchAfk(
  folder: string,
  enabled: boolean,
  fetchMinutes: () => Promise<number>,
  now: () => number = Date.now,
): Promise<boolean> {
  try {
    if (enabled) writeAfk(folder, await fetchMinutes(), now())
    else clearAfk(folder)
    return true
  } catch (error) {
    console.error(JSON.stringify({ event: 'afk-switch-failed', enabled, error: String(error) }))
    return false
  }
}
