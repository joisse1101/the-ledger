import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { registerWorkoutHandler, registerWorkoutScheme, resolveWorkoutUrl, WORKOUT_SCHEME } from '../src/main/workoutProtocol'
import type { WorkoutFolders } from '../src/main/workouts'

let temp: string
let folders: WorkoutFolders

beforeEach(() => {
  temp = fs.mkdtempSync(path.join(os.tmpdir(), 'ledger-protocol-'))
  folders = { starter: path.join(temp, 'starter'), personal: path.join(temp, 'mine') }
  fs.mkdirSync(path.join(folders.starter, 's'), { recursive: true })
  fs.mkdirSync(folders.personal)
  fs.writeFileSync(path.join(folders.starter, 's', 'a.svg'), 'x')
  fs.writeFileSync(path.join(folders.personal, 'my clip.mp4'), 'x')
  fs.writeFileSync(path.join(temp, 'secret.txt'), 'x')
})

afterEach(() => {
  fs.rmSync(temp, { recursive: true })
})

describe('resolveWorkoutUrl', () => {
  it('resolves a file in the starter folder and one with an encoded space in the personal folder', () => {
    expect(resolveWorkoutUrl('ledger-workout://starter/s/a.svg', folders)).toBe(
      fs.realpathSync(path.join(folders.starter, 's', 'a.svg')),
    )
    expect(resolveWorkoutUrl('ledger-workout://mine/my%20clip.mp4', folders)).toBe(
      fs.realpathSync(path.join(folders.personal, 'my clip.mp4')),
    )
  })

  it.each([
    ['an unknown root', 'ledger-workout://other/a.svg'],
    ['a parent-folder climb', 'ledger-workout://starter/%2e%2e/secret.txt'],
    ['an encoded separator climb', 'ledger-workout://starter/s/..%2f..%2fsecret.txt'],
    ['a missing file', 'ledger-workout://starter/s/none.svg'],
    ['another scheme', 'file:///etc/passwd'],
    ['a malformed escape', 'ledger-workout://starter/%zz'],
    ['no path', 'ledger-workout://starter/'],
  ])('returns null for %s', (_name, url) => {
    expect(resolveWorkoutUrl(url, folders)).toBeNull()
  })

  it('returns null for a link leaving the root', () => {
    const outside = path.join(temp, 'outside')
    fs.mkdirSync(outside)
    fs.writeFileSync(path.join(outside, 'x.png'), 'x')
    fs.symlinkSync(outside, path.join(folders.personal, 'link'), 'junction')
    expect(resolveWorkoutUrl('ledger-workout://mine/link/x.png', folders)).toBeNull()
  })
})

describe('registerWorkoutHandler', () => {
  const setup = () => {
    let handler: ((request: Request) => Response | Promise<Response>) | undefined
    const protocol = {
      registerSchemesAsPrivileged: vi.fn(),
      handle: vi.fn((_scheme: string, fn: typeof handler) => {
        handler = fn
      }),
    }
    const net = { fetch: vi.fn(async () => new Response('file', { status: 206 })) }
    registerWorkoutHandler(protocol as never, net as never, folders)
    return { protocol, net, call: (url: string, headers?: Record<string, string>) => handler!(new Request(url, { headers })) }
  }

  it('answers 404 outside the roots and reads no file', async () => {
    const { net, call } = setup()
    const response = await call('ledger-workout://starter/%2e%2e/secret.txt')
    expect(response.status).toBe(404)
    expect(net.fetch).not.toHaveBeenCalled()
  })

  it('passes a Range header on when serving a file', async () => {
    const { net, call, protocol } = setup()
    const response = await call('ledger-workout://starter/s/a.svg', { Range: 'bytes=0-9' })
    expect(response.status).toBe(206)
    expect(protocol.handle).toHaveBeenCalledWith(WORKOUT_SCHEME, expect.any(Function))
    const [fileUrl, init] = (net.fetch.mock.calls[0] as unknown) as [string, { headers: Headers }]
    expect(fileUrl.startsWith('file:///')).toBe(true)
    expect(init.headers.get('range')).toBe('bytes=0-9')
  })
})

describe('registerWorkoutScheme', () => {
  it('registers the scheme as standard, secure, streaming and fetch-capable', () => {
    const protocol = { registerSchemesAsPrivileged: vi.fn() }
    registerWorkoutScheme(protocol as never)
    expect(protocol.registerSchemesAsPrivileged).toHaveBeenCalledWith([
      { scheme: 'ledger-workout', privileges: { standard: true, secure: true, stream: true, supportFetchAPI: true } },
    ])
  })
})
