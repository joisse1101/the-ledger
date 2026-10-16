import { afterEach, describe, expect, it } from 'vitest'
import { createApi } from '../src/main/api'
import { json, startStub, type Stub } from './stubServer'

let stub: Stub | undefined
afterEach(async () => {
  await stub?.close()
  stub = undefined
})

const session = { session_id: 's1', project: 'p', git_branch: 'main', context: { label: '394k' }, pending_decision: null }

describe('fetchLive', () => {
  it('returns the sessions when the backend answers', async () => {
    stub = await startStub((_req, res) => json(res, 200, { sessions: [session] }))
    const result = await createApi(stub.port).fetchLive()
    expect(result).toEqual({ state: 'online', sessions: [session] })
    expect(stub.requests[0].url).toBe('/api/live')
    expect(stub.requests[0].headers.host).toBe(`127.0.0.1:${stub.port}`)
  })

  it('is offline on a non-200 and carries no rows', async () => {
    stub = await startStub((_req, res) => json(res, 500, { sessions: [session] }))
    expect(await createApi(stub.port).fetchLive()).toEqual({ state: 'offline' })
  })

  it('is offline on a malformed body', async () => {
    stub = await startStub((_req, res) => json(res, 200, { nope: true }))
    expect(await createApi(stub.port).fetchLive()).toEqual({ state: 'offline' })
  })

  it('is offline when the connection is refused', async () => {
    stub = await startStub((_req, res) => json(res, 200, {}))
    const port = stub.port
    await stub.close()
    stub = undefined
    expect(await createApi(port).fetchLive()).toEqual({ state: 'offline' })
  })

  it('is offline when the backend does not answer in time', async () => {
    stub = await startStub(() => {
      /* never respond */
    })
    expect(await createApi(stub.port, fetch, 100).fetchLive()).toEqual({ state: 'offline' })
  })
})

describe('openRepo', () => {
  it('POSTs with the CSRF header and reports opened', async () => {
    stub = await startStub((_req, res) => json(res, 200, { opened: 's1' }))
    expect(await createApi(stub.port).openRepo('s1')).toBe('opened')
    expect(stub.requests[0].method).toBe('POST')
    expect(stub.requests[0].url).toBe('/api/sessions/s1/open-repo')
    expect(stub.requests[0].headers['x-requested-with']).toBe('ledger')
  })

  it('reports ended on 404', async () => {
    stub = await startStub((_req, res) => json(res, 404, { detail: 'unknown or not-live session' }))
    expect(await createApi(stub.port).openRepo('s1')).toBe('ended')
  })

  it('reports failed on other statuses', async () => {
    stub = await startStub((_req, res) => json(res, 403, {}))
    expect(await createApi(stub.port).openRepo('s1')).toBe('failed')
  })

  it('reports failed on a network error', async () => {
    stub = await startStub((_req, res) => json(res, 200, {}))
    const port = stub.port
    await stub.close()
    stub = undefined
    expect(await createApi(port).openRepo('s1')).toBe('failed')
  })
})

describe('backendUp', () => {
  it('is true when /api/meta answers and false otherwise', async () => {
    stub = await startStub((_req, res) => json(res, 200, {}))
    const api = createApi(stub.port)
    expect(await api.backendUp()).toBe(true)
    await stub.close()
    stub = undefined
    expect(await api.backendUp()).toBe(false)
  })
})

const meta = (remote_mode: unknown) => ({ refreshed_at: null, is_local: true, remote_mode })
const remoteOff = { enabled: false, expires_at: null, state: 'off', step: null, reason: null }

describe('fetchRemote', () => {
  it.each([
    [remoteOff, { state: 'off' }],
    [{ ...remoteOff, state: 'starting', step: 'gateway' }, { state: 'starting', step: 'gateway' }],
    [{ ...remoteOff, state: 'starting', step: 'nonsense' }, { state: 'starting', step: null }],
    [
      { ...remoteOff, enabled: true, state: 'ready', expires_at: '2026-10-16T20:00:00+00:00' },
      { state: 'ready', expiresAt: '2026-10-16T20:00:00+00:00' },
    ],
    [
      { ...remoteOff, state: 'failed', reason: 'Docker Desktop is not installed' },
      { state: 'failed', reason: 'Docker Desktop is not installed' },
    ],
    [{ ...remoteOff, state: 'failed', reason: null }, { state: 'failed', reason: 'Remote mode could not start' }],
    [{ state: 'mystery' }, { state: 'unavailable' }],
    [null, { state: 'unavailable' }],
  ])('reads %j as %j', async (remote, expected) => {
    stub = await startStub((_req, res) => json(res, 200, meta(remote)))
    expect(await createApi(stub.port).fetchRemote()).toEqual(expected)
    expect(stub.requests[0].url).toBe('/api/meta')
  })

  it('is unavailable on a non-200, and when nothing answers', async () => {
    stub = await startStub((_req, res) => json(res, 500, meta(remoteOff)))
    expect(await createApi(stub.port).fetchRemote()).toEqual({ state: 'unavailable' })
    const port = stub.port
    await stub.close()
    stub = undefined
    expect(await createApi(port).fetchRemote()).toEqual({ state: 'unavailable' })
  })
})

describe('setRemoteMode', () => {
  it('POSTs the choice with the CSRF header and returns the state the backend reports', async () => {
    stub = await startStub((_req, res) => json(res, 200, { ...remoteOff, state: 'starting', step: 'docker' }))
    expect(await createApi(stub.port).setRemoteMode(true)).toEqual({ state: 'starting', step: 'docker' })
    const request = stub.requests[0]
    expect(request.method).toBe('POST')
    expect(request.url).toBe('/api/remote-mode')
    expect(request.headers['x-requested-with']).toBe('ledger')
    expect(request.headers['content-type']).toBe('application/json')
  })

  it('sends enabled: false to turn it off', async () => {
    let body = ''
    stub = await startStub((req, res) => {
      req.on('data', (chunk) => (body += chunk))
      req.on('end', () => json(res, 200, remoteOff))
    })
    expect(await createApi(stub.port).setRemoteMode(false)).toEqual({ state: 'off' })
    expect(JSON.parse(body)).toEqual({ enabled: false })
  })

  it('is unavailable when the backend refuses', async () => {
    stub = await startStub((_req, res) => json(res, 403, { detail: 'requires a local request' }))
    expect(await createApi(stub.port).setRemoteMode(true)).toEqual({ state: 'unavailable' })
  })
})

describe('fetchQr', () => {
  it('returns the code and the token-free address', async () => {
    stub = await startStub((_req, res) =>
      json(res, 200, { svg: '<svg/>', display_url: 'https://192.168.1.20:8080', expires_at: null }),
    )
    expect(await createApi(stub.port).fetchQr()).toEqual({ svg: '<svg/>', displayUrl: 'https://192.168.1.20:8080' })
    expect(stub.requests[0].url).toBe('/api/remote-mode/qr')
  })

  it('is null when Remote mode is not ready', async () => {
    stub = await startStub((_req, res) => json(res, 409, { detail: 'Remote mode is not ready' }))
    expect(await createApi(stub.port).fetchQr()).toBeNull()
  })

  it('is null when the body is not a code', async () => {
    stub = await startStub((_req, res) => json(res, 200, { svg: 3 }))
    expect(await createApi(stub.port).fetchQr()).toBeNull()
  })
})
