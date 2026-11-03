import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { pollLiveAndAfk, writeAfk, CHIME_SCRIPT } from '../src/main/afk'
import { createApi } from '../src/main/api'
import { BreakTimer, breakCountdown } from '../src/main/breakTimer'
import { CHANNELS } from '../src/shared/ipc'
import { startStub, type Stub } from './stubServer'

describe('preload channels', () => {
  it('uses exactly the channel names in shared/ipc.ts', () => {
    const preloads = ['index.ts', 'tooltip.ts', 'breakWindow.ts'].map((file) =>
      fs.readFileSync(path.join(__dirname, '..', 'src', 'preload', file), 'utf8'),
    )
    const used = preloads.flatMap((source) => [...source.matchAll(/'(widget:[a-z-]+)'/g)].map((m) => m[1]))
    expect(new Set(used)).toEqual(new Set(Object.values(CHANNELS)))
  })

  it('has the preload listen on the break countdown channel', () => {
    const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'preload', 'index.ts'), 'utf8')
    expect(CHANNELS.breakCountdown).toBe('widget:break-countdown')
    expect(source).toContain(`on('${CHANNELS.breakCountdown}'`)
  })

  it('has the AFK channels, one to push the flag and one to change it', () => {
    expect(CHANNELS.afkState).toBe('widget:afk-state')
    expect(CHANNELS.setAfk).toBe('widget:set-afk')
  })

  it('has the preload send the AFK press on the setAfk channel', () => {
    const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'preload', 'index.ts'), 'utf8')
    expect(source).toContain(`invoke('${CHANNELS.setAfk}', enabled)`)
    expect(source).toContain(`on('${CHANNELS.afkState}'`)
  })
})

describe('the break countdown pushed each second', () => {
  let time = 0
  const timer = () => new BreakTimer(() => time)
  const work = (t: BreakTimer, seconds: number, afkOn = false) => {
    for (let i = 0; i < seconds; i += 1) {
      time += 1000
      t.tick(afkOn, 60)
    }
  }

  it('carries the seconds left while counting', () => {
    const t = timer()
    work(t, 18 * 60)
    expect(breakCountdown(t, false, 60, false)).toEqual({ remainingSeconds: 42 * 60, paused: false })
  })

  it('marks the value paused and unchanged while AFK is on', () => {
    const t = timer()
    work(t, 18 * 60)
    work(t, 60, true)
    expect(breakCountdown(t, true, 60, false)).toEqual({ remainingSeconds: 42 * 60, paused: true })
  })

  it('carries 0 when a break is due', () => {
    const t = timer()
    work(t, 60 * 60)
    expect(breakCountdown(t, false, 60, false)).toEqual({ remainingSeconds: 0, paused: false })
  })

  it('carries 0 while the break window is open', () => {
    const t = timer()
    work(t, 60)
    expect(breakCountdown(t, false, 60, true)).toEqual({ remainingSeconds: 0, paused: false })
  })
})

describe('the state pushed on each poll', () => {
  let stub: Stub | undefined
  let folder = ''
  afterEach(async () => {
    await stub?.close()
    stub = undefined
    if (folder) fs.rmSync(folder, { recursive: true })
    folder = ''
  })

  it('carries the AFK flag while the backend is unreachable', async () => {
    folder = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-ipc-'))
    fs.writeFileSync(path.join(folder, CHIME_SCRIPT), '# mock')
    writeAfk(folder, 20)
    stub = await startStub((_req, res) => res.end())
    const port = stub.port
    await stub.close()
    stub = undefined

    const { live, afk } = await pollLiveAndAfk(() => createApi(port).fetchLive(), folder)

    expect(live).toEqual({ state: 'offline' })
    expect(afk).toMatchObject({ installed: true, on: true })
    expect(afk.minutesLeft).toBeGreaterThanOrEqual(19)
  })
})
