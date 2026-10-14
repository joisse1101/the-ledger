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
